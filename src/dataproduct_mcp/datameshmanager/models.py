from typing import Optional
from pydantic import BaseModel, Field


class AccessStatusResult(BaseModel):
    """Response model for access status endpoint."""
    
    data_product_id: Optional[str] = Field(None, alias="dataProductId")
    output_port_id: Optional[str] = Field(None, alias="outputPortId")
    data_contract_id: Optional[str] = Field(None, alias="dataContractId")
    output_port_type: Optional[str] = Field(None, alias="outputPortType")
    can_get_instant_access: Optional[bool] = Field(None, alias="canGetInstantAccess")
    can_get_instant_access_reason: Optional[str] = Field(None, alias="canGetInstantAccessReason")
    access_id: Optional[str] = Field(None, alias="accessId")
    access_status: Optional[str] = Field(None, alias="accessStatus")
    access_lifecycle_status: Optional[str] = Field(None, alias="accessLifecycleStatus")
    can_request_access: Optional[bool] = Field(None, alias="canRequestAccess")
    can_request_access_reason: Optional[str] = Field(None, alias="canRequestAccessReason")

    model_config = {
        "populate_by_name": True
    }


class RequestAccessRequest(BaseModel):
    """Request model for requesting access to an output port."""
    
    purpose: str = Field(..., description="The purpose/reason for requesting access to the data")

    model_config = {
        "populate_by_name": True
    }


class RequestAccessResult(BaseModel):
    """Response model for request access endpoint."""
    
    access_id: str = Field(..., alias="accessId")
    status: str = Field(..., description="The status of the access request")

    model_config = {
        "populate_by_name": True
    }
