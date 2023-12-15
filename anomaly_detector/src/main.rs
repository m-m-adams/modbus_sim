use pcap::Capture;
use nom::{number, IResult, Finish};
use pktparse::{ethernet, ipv4, tcp};
use sawp::parser::{Direction, Parse};
use sawp::error::Error;
use sawp::error::ErrorKind;
use sawp_modbus::{Modbus, Message};


fn parse_modbus(input: &[u8]) -> std::result::Result<&[u8], Error> {
    let modbus = Modbus::default();
    let mut bytes = input;
    while bytes.len() > 0 {
        // If we know that this is a request or response, change the Direction
        // for a more accurate parsing
        match modbus.parse(bytes, Direction::Unknown) {
            // The parser succeeded and returned the remaining bytes and the parsed modbus message
            Ok((rest, Some(message))) => {
                println!("Modbus message: {:?}", message);
                bytes = rest;
            }
            // The parser recognized that this might be modbus and made some progress,
            // but more bytes are needed
            Ok((rest, None)) => return Ok(rest),
            // The parser was unable to determine whether this was modbus or not and more
            // bytes are needed
            Err(Error { kind: ErrorKind::Incomplete(_) }) => return Ok(bytes),
            // The parser determined that this was not modbus
            Err(e) => return Err(e)
        }
    }
    Ok(bytes)
}
fn main() {

let mut cap = Capture::from_file("../tcpdump/tcpdump.pcap").unwrap();

while let Ok(packet) = cap.next_packet() {

        if let Ok((remaining, eth_frame)) = ethernet::parse_ethernet_frame(packet.data) {
            if eth_frame.ethertype != ethernet::EtherType::IPv4 {
                continue;
            }
            println!("{:?}", eth_frame);
            let (remaining, _) = number::streaming::be_u16::<_, (_, nom::error::ErrorKind)>(remaining).unwrap();

            if let Ok((remaining, ipv4_packet) )= ipv4::parse_ipv4_header(remaining) {
                println!("{:?}", ipv4_packet);
                if let Ok((remaining, _tcp_packet) )= tcp::parse_tcp_header(remaining) {
                    println!("{:?}", _tcp_packet);
                _ =parse_modbus(remaining);
            }
        }
    }
}
}
