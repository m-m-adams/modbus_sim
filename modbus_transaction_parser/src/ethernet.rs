use nom::{bytes, number, IResult};

pub use pktparse::ethernet::{EtherType, MacAddress};

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
