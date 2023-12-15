use pcap::Capture;
use nom::{number, IResult, Finish, bytes};
use pktparse::{ethernet, ipv4, tcp};
use pktparse::ethernet::{MacAddress, EtherType};
use sawp::parser::{Direction, Parse};
use sawp::error::Error;
use sawp::error::ErrorKind;
use sawp_modbus::{Modbus, Message};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[cfg_attr(feature = "serde", derive(serde::Serialize, serde::Deserialize))]
pub struct EthernetFrame {
    pub direction: u16,
    pub ethtype: u16,
    pub addr_length: u16,
    pub source_mac: MacAddress,
    pub ethertype: EtherType,
}

pub(crate) fn mac_address(input: &[u8]) -> IResult<&[u8], MacAddress> {
    let (input, mac) = bytes::streaming::take(6u8)(input)?;

    Ok((input, MacAddress(<[u8; 6]>::try_from(mac).unwrap())))
}

fn parse_ethertype(input: &[u8]) -> IResult<&[u8], EtherType> {
    let (input, _) = number::streaming::be_u16(input)?;
    let (input, ether) = number::streaming::be_u16(input)?;

    Ok((input, ether.into()))
}
pub fn parse_ethernet_frame(input: &[u8]) -> IResult<&[u8], EthernetFrame> {
    let (input, direction) = number::streaming::be_u16(input)?;
    let (input, ethtype) = number::streaming::be_u16(input)?;
    let (input, addr_length) = number::streaming::be_u16(input)?;
    let (input, source_mac) = mac_address(input)?;
    let (input, ethertype) = parse_ethertype(input)?;

    Ok((
        input,
        EthernetFrame {
            direction,
            ethtype,
            addr_length,
            source_mac,
            ethertype,
        },
    ))
}

fn parse_modbus(input: &[u8], direction: Direction) -> std::result::Result<&[u8], Error> {
    let modbus = Modbus::default();
    let mut bytes = input;
    while bytes.len() > 0 {
        // If we know that this is a request or response, change the Direction
        // for a more accurate parsing
        match modbus.parse(bytes, direction.clone()) {
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
fn main() -> Result<(), nom::error::ErrorKind> {

let mut cap = Capture::from_file("../tcpdump/tcpdump.pcap").unwrap();

    while let Ok(packet) = cap.next_packet() {

            if let Ok((remaining, eth_frame)) = parse_ethernet_frame(packet.data) {

                if eth_frame.ethertype != ethernet::EtherType::IPv4 {
                    println!("{:?}", eth_frame);
                    continue;
                }

                println!("{:?}", eth_frame);

                if let Ok((remaining, ipv4_packet) )= ipv4::parse_ipv4_header(remaining) {
                    println!("{:?}", ipv4_packet);
                    if let Ok((remaining, tcp_packet) )= tcp::parse_tcp_header(remaining) {
                        println!("{:?}", tcp_packet);
                        let direction: Direction;
                        match tcp_packet.source_port {
                            502 => direction = Direction::ToClient,
                            _ => direction = Direction::ToServer,

                        }
                    _ =parse_modbus(remaining, direction);
                }
            }
        }
    }
    return Ok(())
}
