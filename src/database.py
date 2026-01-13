import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, joinedload
import config

Base = declarative_base()

class SourceFile(Base):
    __tablename__ = 'source_files'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    
    # 新增: 檔案路徑，讓 API 可以提供給前端播放
    file_path = Column(String, nullable=True)
    
    author = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata_info = Column(JSONB, nullable=True)

    contents = relationship("Content", back_populates="source_file", cascade="all, delete-orphan")

class Content(Base):
    __tablename__ = 'contents'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_file_id = Column(UUID(as_uuid=True), ForeignKey('source_files.id'), nullable=False)
    type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    custom = Column(JSONB, nullable=True)

    source_file = relationship("SourceFile", back_populates="contents")

def get_engine():
    return create_engine(config.POSTGRES_URL)

def init_db():
    """建立資料表"""
    engine = get_engine()
    Base.metadata.create_all(engine)
    print("PostgreSQL tables updated (source_files, contents).")

def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()

def get_contents_by_ids(session, id_list):
    """根據 ID 列表查詢內容與關聯的影片資訊，使用 joinedload 預載"""
    uuid_list = [uuid.UUID(id_str) for id_str in id_list]
    
    # joinedload 確保 source_file 在 session 關閉前就被載入
    results = (
        session.query(Content)
        .options(joinedload(Content.source_file))
        .filter(Content.id.in_(uuid_list))
        .all()
    )
    return results