use easy_error::{bail, Error};
use pcap::Capture;
use pktparse::{ipv4, tcp, ethernet};
use sawp::error::ErrorKind;
use sawp::parser::{Direction, Parse};
use sawp_modbus as modbus;
use sawp_modbus::Modbus;
use std::collections::HashMap;
use std::fs::File;
use std::io::{stdout, BufWriter, Write};
use structopt::StructOpt;
use std::path::PathBuf;
mod modbus_defs;
use modbus_defs::*;

#[derive(Debug, StructOpt)]
#[structopt(name = "Inputs", about = "Provide input and optional output paths")]
struct Opt {

    /// Input file
    #[structopt(parse(from_os_str))]
    input: PathBuf,

    /// Output file, stdout if not present
    #[structopt(parse(from_os_str))]
    output: Option<PathBuf>,

}

fn parse_modbus(input: &[u8], direction: Direction) -> std::result::Result<Option<modbus::Message>, Error> {
    let modbus = Modbus::default();
    let bytes = input;

    // If we know that this is a request or response, change the Direction
    // for a more accurate parsing
    match modbus.parse(bytes, direction.clone()) {
        // The parser succeeded and returned the remaining bytes and the parsed modbus message
        Ok((_rest, Some(message))) => {
            return Ok(Some(message));
        }
        // The parser recognized that this might be modbus and made some progress,
        // but more bytes are needed
        Ok((_rest, None)) => bail!("not parsed"),
        // The parser was unable to determine whether this was modbus or not and more
        // bytes are needed
        Err(sawp::error::Error {
            kind: ErrorKind::Incomplete(_),
        }) => return Ok(None),
        // The parser determined that this was not modbus
        Err(_) => bail!("other error"),
    }
}
fn main() {
    let opt = Opt::from_args();
    let mut cap = Capture::from_file(opt.input).unwrap();
    let mut writer: BufWriter<Box<dyn std::io::Write>> = match opt.output {
        Some(path) => {
            let file = File::create(path).unwrap();
            BufWriter::new(Box::new(file))
        },
        None => {
            BufWriter::new(Box::new(stdout().lock()))
        }
    };
    
    let mut sessions: HashMap<u16,modbus::Message> = HashMap::new();
    while let Ok(packet) = cap.next_packet() {
        let time = packet.header.ts.tv_sec;
        if let Ok((remaining, eth_frame)) = ethernet::parse_ethernet_frame(packet.data) {
            if eth_frame.ethertype != ethernet::EtherType::IPv4 {
                //println!("{:?}", eth_frame);
                continue;
            }

            //println!("{:?}", eth_frame);

            if let Ok((remaining, _ipv4_packet)) = ipv4::parse_ipv4_header(remaining) {
                //println!("{:?}", ipv4_packet);
                if let Ok((remaining, tcp_packet)) = tcp::parse_tcp_header(remaining) {
                    //println!("{:?}", tcp_packet);
                    let direction: Direction;
                    match tcp_packet.source_port {
                        502 => direction = Direction::ToClient,
                        _ => direction = Direction::ToServer,
                    }
                    match parse_modbus(remaining, direction) {
                        Ok(Some(mut message)) => {
                            if !message.error_flags.is_empty() {
                                panic!("{:?}", message);
                            }
                            match sessions.remove_entry(&message.transaction_id) {
                                Some(request) => {
                                    let function = request.1.function.code;
                                    let access = request.1.access_type;
                                    let valid: bool = message.matches(&request.1);
                                    let _mult = access.intersects(modbus::AccessType::MULTIPLE);
                                    //this ignores all the cases that aren't present in the data which is gross but here we are
                                    let (data, data_coils): (Option<u16>, Option<bool>) =
                                        match access.intersects(modbus::AccessType::COILS) {
                                            false => {
                                                let data: Option<u16> = match message.data {
                                                    modbus::Data::Read(modbus::Read::Response(data)) => {
                                                        Some(u16::from_be_bytes(
                                                            (data[0], data[1]).into(),
                                                        ))
                                                    }

                                                    modbus::Data::Write(modbus::Write::Other {
                                                        address: _,
                                                        data,
                                                    }) => Some(data),
                                                    _ => None,
                                                };
                                                let data_coils = None;
                                                (data, data_coils)
                                            }
                                            true => {
                                                let data: Option<bool> = match message.data {
                                                    modbus::Data::Read(modbus::Read::Response(data)) => {
                                                        Some(match data[0] {
                                                            0 => false,
                                                            _ => true,
                                                        })
                                                    }
                                                    modbus::Data::Write(modbus::Write::Other {
                                                        address: _,
                                                        data,
                                                    }) => Some(match data {
                                                        0 => false,
                                                        _ => true,
                                                    }),
                                                    _ => None,
                                                };
                                                (None, data)
                                            }
                                        };
                                    let address = match request.1.data {
                                        modbus::Data::Read(modbus::Read::Request {
                                            address,
                                            quantity: _,
                                        }) => address,
                                        modbus::Data::Write(modbus::Write::Other { address, data: _ }) => address,
                                        _ => 0,
                                    };

                                    let trans = Transaction {
                                        time,
                                        transaction_id: message.transaction_id,
                                        valid,
                                        unit_id: message.unit_id,
                                        function,
                                        address: address,
                                        response_data: data,
                                        response_coils: data_coils,
                                    };
                                    writeln!(writer, "{}", serde_json::to_string(&trans).unwrap()).unwrap();
                                }
                                None => {
                                    sessions.insert(message.transaction_id, message);
                                }
                            }
                        }
                        Err(_e) => {}
                        Ok(None) => {}
                    }
                }
            }
        }
    }
}
