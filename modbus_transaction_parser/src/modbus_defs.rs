use sawp_modbus::{Data, FunctionCode, Message, Modbus, Read, Write};
use serde::Serialize;

#[derive(Serialize)]
#[serde(remote = "FunctionCode")]
pub enum FunctionCodeDef {
    RdCoils = 0x01,
    RdDiscreteInputs,
    RdHoldRegs,
    RdInputRegs,
    WrSingleCoil,
    WrSingleReg,
    RdExcStatus,
    Diagnostic,
    Program484,
    Poll484,
    GetCommEventCtr,
    GetCommEventLog,
    ProgramController,
    PollController,
    WrMultCoils,
    WrMultRegs,
    ReportServerID,
    Program884,
    ResetCommLink,
    RdFileRec,
    WrFileRec,
    MaskWrReg,
    RdWrMultRegs,
    RdFIFOQueue,
    MEI = 0x2b,
    Unknown,
}

/// Breakdown of the parsed modbus transaction
#[derive(Debug, PartialEq, Serialize)]
pub struct Transaction {
    pub time: i64,
    pub transaction_id: u16,
    pub valid: bool,
    pub unit_id: u8,
    #[serde(with = "FunctionCodeDef")]
    pub function: FunctionCode,
    pub address: u16,
    pub response_data: Option<u16>,
    pub response_coils: Option<bool>,
}
