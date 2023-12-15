use easy_error::{bail, Error};
use pcap::Capture;
use pktparse::{ipv4, tcp};
use sawp::error::ErrorKind;
use sawp::parser::{Direction, Parse};
use sawp_modbus::{AccessType, Data, Message, Modbus, Read, Write};
use std::collections::HashMap;
mod ethernet;
mod modbus_defs;
use ethernet::*;
use modbus_defs::*;

fn parse_modbus(input: &[u8], direction: Direction) -> std::result::Result<Option<Message>, Error> {
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
    let mut cap = Capture::from_file("../tcpdump/tcpdump.pcap").unwrap();

    let mut sessions: HashMap<u16, Message> = HashMap::new();
    while let Ok(packet) = cap.next_packet() {
        let time = packet.header.ts.tv_sec;
        if let Ok((remaining, eth_frame)) = parse_ethernet_frame(packet.data) {
            if eth_frame.ethertype != ethernet::EtherType::IPv4 {
                // println!("{:?}", eth_frame);
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
                                    let mult = access.intersects(AccessType::MULTIPLE);
                                    //this ignores all the cases that aren't present in the data which is gross but here we are
                                    let (data, data_coils): (Option<u16>, Option<bool>) =
                                        match access.intersects(AccessType::COILS) {
                                            false => {
                                                let data: Option<u16> = match message.data {
                                                    Data::Read(Read::Response(data)) => {
                                                        Some(u16::from_be_bytes(
                                                            (data[0], data[1]).into(),
                                                        ))
                                                    }

                                                    Data::Write(Write::Other {
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
                                                    Data::Read(Read::Response(data)) => {
                                                        Some(match data[0] {
                                                            0 => false,
                                                            _ => true,
                                                        })
                                                    }
                                                    Data::Write(Write::Other {
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
                                        Data::Read(Read::Request {
                                            address,
                                            quantity: _,
                                        }) => address,
                                        Data::Write(Write::Other { address, data: _ }) => address,
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
                                    println!("{}", serde_json::to_string(&trans).unwrap());
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
