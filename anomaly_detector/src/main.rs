use pcap::Capture;
use serde::{Deserialize, Serialize};
use serde_json::Result;
use std::collections::HashMap;
use easy_error::{bail, Error};
use pktparse::{ipv4, tcp};
use sawp::parser::{Direction, Parse};
use sawp::error::ErrorKind;
use sawp_modbus::{Modbus, Message, Data, FunctionCode, Flags, AccessType, CodeCategory, ErrorFlags, Read, Write};
mod ethernet;
use ethernet::{*};


/// Breakdown of the parsed modbus transaction
#[derive(Debug, PartialEq, Serialize)]
pub struct Transaction {
    pub time: i64,
    pub transaction_id: u16,
    pub valid: bool,
    pub unit_id: u8,
    pub function: u8,
    pub address: u16,
    pub response_data: Vec<u8>,

}




fn parse_modbus(input: &[u8], direction: Direction) -> std::result::Result<Option<Message>, Error> {
    let modbus = Modbus::default();
    let  bytes = input;

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
        Err(sawp::error::Error { kind: ErrorKind::Incomplete(_) }) => return Ok(None),
        // The parser determined that this was not modbus
        Err(_) => bail!("other error")
    }
    

}
fn main()  {

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

                if let Ok((remaining, _ipv4_packet) )= ipv4::parse_ipv4_header(remaining) {
                    //println!("{:?}", ipv4_packet);
                    if let Ok((remaining, tcp_packet) )= tcp::parse_tcp_header(remaining) {
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
                                    let valid:bool = message.matches(&request.1);
                                    let data = match message.data {
                                        Data::Read(Read::Response(data)) => data,
                                        Data::Write(Write::Other { address, data }) => data.to_be_bytes().to_vec(),
                                        _ => vec!(),
                                    };
                                    let address = match request.1.data {
                                        Data::Read(Read::Request { address, quantity }) => address,
                                        Data::Write(Write::Other { address, data }) => address,
                                        _ => 0,
                                    };

                                    let trans = Transaction{
                                        time,
                                        transaction_id: message.transaction_id,
                                        valid,
                                        unit_id: message.unit_id,
                                        function: request.1.function.raw,
                                        address: address,
                                        response_data: data,

                                    };
                                    println!("{:x?}", trans);
                                }
                                None => {sessions.insert(message.transaction_id, message);},
                            }
                        }
                        Err(e) => {
                            println!("Error parsing modbus {:?}", e);
                        }
                        Ok(None) => {
                            println!("Not modbus");
                        }
                    }
                    
                }
            }
        }
    }

}
