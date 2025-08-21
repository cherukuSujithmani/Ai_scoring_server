# app/models/types.py
from typing import List, Optional
from pydantic import BaseModel, Field


class TokenAmount(BaseModel):
    amount: Optional[float] = 0.0
    amountUSD: Optional[float] = 0.0
    address: Optional[str] = ""
    symbol: Optional[str] = ""


class DexTransaction(BaseModel):
    document_id: str
    action: str
    timestamp: int

    caller: Optional[str] = ""
    protocol: Optional[str] = ""
    poolId: Optional[str] = ""
    poolName: Optional[str] = ""

    tokenIn: Optional[TokenAmount] = None
    tokenOut: Optional[TokenAmount] = None
    token0: Optional[TokenAmount] = None
    token1: Optional[TokenAmount] = None


class ProtocolData(BaseModel):
    protocolType: str
    transactions: List[DexTransaction] = Field(default_factory=list)


class WalletMessage(BaseModel):
    wallet_address: str = Field(..., alias="wallet_address")
    data: List[ProtocolData] = Field(default_factory=list)
