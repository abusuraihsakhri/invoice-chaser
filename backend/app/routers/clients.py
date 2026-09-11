from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import User, Client
from app.schemas import ClientCreate, ClientUpdate, ClientResponse
from app.services.integrations.export_service import export_clients_to_csv

router = APIRouter(prefix="/api/clients", tags=["clients"])


@router.get("", response_model=List[ClientResponse])
def list_clients(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(Client).filter(Client.user_id == current_user.id).order_by(Client.name.asc()).all()


@router.get("/export/csv")
def export_clients_csv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    clients = db.query(Client).filter(Client.user_id == current_user.id).order_by(Client.name.asc()).all()
    csv_data = export_clients_to_csv(clients)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="clients_export.csv"'},
    )


@router.post("", response_model=ClientResponse)
def create_client(
    client_data: ClientCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    client = Client(
        user_id=current_user.id,
        name=client_data.name,
        email=client_data.email,
        company=client_data.company,
        phone=client_data.phone,
        notes=client_data.notes,
        risk_score=15.0,
        risk_tier="low",
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.put("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int,
    client_data: ClientUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.user_id == current_user.id,
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    update_data = client_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)

    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.user_id == current_user.id,
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    db.delete(client)
    db.commit()

