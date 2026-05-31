from pydantic import BaseModel, Field
from typing import List, Optional

class CompanyData(BaseModel):
    market_cap: str = Field(default="-", description="Market Cap in Rs. cr")
    high_low: str = Field(default="-", description="52 Week High - Low in Rs.")
    enterprise_value: str = Field(default="-", description="Enterprise Value in Rs. cr")
    outstanding_shares: str = Field(default="-", description="Outstanding Shares in cr")
    free_float: str = Field(default="-", description="Free Float in %")
    dividend_yield: str = Field(default="-", description="Dividend Yield in %")
    avg_volume: str = Field(default="-", description="6m average volume in cr")
    beta: str = Field(default="-", description="Beta")
    face_value: str = Field(default="-", description="Face value in Rs.")

class ShareholdingQuarter(BaseModel):
    quarter: str = Field(description="Quarter name, e.g., Q3FY25")
    promoters: str = Field(default="-", description="Promoters holding %")
    fiis: str = Field(default="-", description="FIIs holding %")
    mfs_institutions: str = Field(default="-", description="MFs/Institutions holding %")
    public: str = Field(default="-", description="Public holding %")
    others: str = Field(default="-", description="Others holding %")
    promoter_pledge: str = Field(default="-", description="Promoter Pledge (e.g. Nil)")

class PricePerformanceRow(BaseModel):
    period: str = Field(description="Period, e.g., 3 Month, 6 Month, 1 Year")
    absolute_return: str = Field(default="-", description="Absolute Return %")
    absolute_sensex: str = Field(default="-", description="Absolute Sensex %")
    relative_return: str = Field(default="-", description="Relative Return %")

class ValuationMetric(BaseModel):
    target: str = Field(default="-", description="Target price in Rs.")
    cmp: str = Field(default="-", description="Current Market Price (CMP) in Rs.")
    upside: str = Field(default="-", description="Expected Return in %")
    rating: str = Field(default="HOLD", description="Rating (BUY, HOLD, SELL, ACCUMULATE, REDUCE)")
    bloomberg: str = Field(default="-", description="Bloomberg Code")
    sensex: str = Field(default="-", description="Sensex value")
    nse_code: str = Field(default="-", description="NSE Code")
    bse_code: str = Field(default="-", description="BSE Code")
    time_frame: str = Field(default="12 Months", description="Time Frame")
    stock_type: str = Field(default="Large Cap", description="Stock Type (e.g., Large Cap, Mid Cap, Small Cap)")

class EstimatesRow(BaseModel):
    metric: str = Field(description="Metric name, e.g., Revenue, EBITDA, Margins (%), Adj. PAT, EPS")
    old_estimate_fy26: str = Field(default="-")
    new_estimate_fy26: str = Field(default="-")
    old_estimate_fy27: str = Field(default="-")
    new_estimate_fy27: str = Field(default="-")
    change_fy26: str = Field(default="-")
    change_fy27: str = Field(default="-")

class StatementRow(BaseModel):
    metric: str = Field(description="Metric name")
    fy23a: str = Field(default="-")
    fy24a: str = Field(default="-")
    fy25a: str = Field(default="-")
    fy26e: str = Field(default="-")
    fy27e: str = Field(default="-")

class FinancialsBundle(BaseModel):
    income_statement: List[StatementRow] = Field(default_factory=list)
    balance_sheet: List[StatementRow] = Field(default_factory=list)
    cash_flow: List[StatementRow] = Field(default_factory=list)
    ratios: List[StatementRow] = Field(default_factory=list)

class GeojitReportData(BaseModel):
    company_name: str = Field(description="Name of the company")
    sector: str = Field(description="Sector the company belongs to")
    report_date: str = Field(description="Date of the report, e.g., 29th July, 2025")
    company_description: str = Field(description="Brief 2-3 sentence description of what the company does")
    highlights: List[str] = Field(description="List of 5-6 bullet points summarizing recent performance")
    outlook_valuation: str = Field(description="Paragraph describing the outlook and valuation, justifying the rating")
    company_data: CompanyData
    shareholding: List[ShareholdingQuarter]
    price_performance: List[PricePerformanceRow]
    valuation: ValuationMetric
    estimates: List[EstimatesRow]
    financials: FinancialsBundle
    recommendation_history: List[dict] = Field(description="List of dicts with 'Date', 'Rating', 'Target'")
