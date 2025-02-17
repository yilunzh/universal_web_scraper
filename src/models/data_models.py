from pydantic import BaseModel, Field
from typing import List

class ModelSales(BaseModel):
    model_name: str = Field(..., description="The name of the car model.")
    units_sold: int = Field(..., description="The number of units sold for this model.")

class ManufacturerSales(BaseModel):
    month: int = Field(..., description="The month for which the sales data is reported.")
    year: int = Field(..., description="The year for which the sales data is reported.")
    manufacturer_name: str = Field(..., description="The name of the car manufacturer.")
    total_units_sold: int = Field(..., description="The total number of units sold.")
    models: List[ModelSales] = Field(..., description="Sales data for each model.")

class DataPoints(BaseModel):
    manufacturers: List[ManufacturerSales] = Field(..., description="Sales data grouped by manufacturer.") 