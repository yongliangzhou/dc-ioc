"""专业域通用概览 API (B5)。

GET /api/domain/{category} 返回该类别下真实 external_devices 列表 (含物模型测点最新值);
零真实设备时返回生成器骨架, 保证新接入类别在页面上可见。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import dc_aggregator as agg

router = APIRouter(prefix="/domain", tags=["domain"])


@router.get("/{category}")
def domain_overview(category: str, db: Session = Depends(get_db)):
    return agg.domain_overview(db, category)
