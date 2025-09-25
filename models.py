from sqlalchemy import create_engine, Column, String, DateTime, Text, Boolean, Float, Integer, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

Base = declarative_base()

# Association table for many-to-many relationship between Newsletter and Article
newsletter_articles = Table(
    'newsletter_articles',
    Base.metadata,
    Column('newsletter_id', UUID(as_uuid=True), ForeignKey('newsletters.id')),
    Column('article_id', UUID(as_uuid=True), ForeignKey('articles.id')),
    Column('section', String(50)),
    Column('position', Integer)
)

class Article(Base):
    __tablename__ = 'articles'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(String(500), unique=True, nullable=False)
    url_canonical = Column(String(500))
    source = Column(String(100), nullable=False)
    published_at = Column(DateTime, nullable=False)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    title = Column(String(500), nullable=False)
    subtitle = Column(Text)
    author = Column(String(200))
    content = Column(Text)
    summary = Column(Text)
    section_detected = Column(String(50))
    sector_tags = Column(Text)  # JSON string
    is_duplicate_of = Column(UUID(as_uuid=True), ForeignKey('articles.id'))
    is_partner_new_fund = Column(Boolean, default=False)
    mentions_acafi = Column(Boolean, default=False)
    evidence = Column(Text)  # JSON string
    relevance_score = Column(Float)
    
    # Relationships
    newsletters = relationship('Newsletter', secondary=newsletter_articles, back_populates='articles')
    duplicate_parent = relationship('Article', remote_side=[id])
    
    def __repr__(self):
        return f"<Article(id={self.id}, title={self.title[:50]}...)>"

class Newsletter(Base):
    __tablename__ = 'newsletters'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = Column(DateTime, nullable=False, unique=True)
    editorial_summary = Column(Text)
    economic_indicators = Column(Text)  # JSON string
    html_body = Column(Text)
    text_body = Column(Text)
    mailchimp_campaign_id = Column(String(100))
    mailchimp_test_sent_to = Column(Text)  # JSON string
    mailchimp_sent_at = Column(DateTime)
    gmail_fallback_message_id = Column(String(100))
    status = Column(String(50), default='draft')  # draft, test_sent, sent, error
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    articles = relationship('Article', secondary=newsletter_articles, back_populates='newsletters')
    logs = relationship('LogEntry', back_populates='newsletter', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Newsletter(id={self.id}, date={self.date}, status={self.status})>"

class LogEntry(Base):
    __tablename__ = 'log_entries'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    newsletter_id = Column(UUID(as_uuid=True), ForeignKey('newsletters.id'))
    timestamp = Column(DateTime, default=datetime.utcnow)
    level = Column(String(20))  # INFO, WARNING, ERROR
    message = Column(Text)
    details = Column(Text)  # JSON string for additional data
    
    # Relationships
    newsletter = relationship('Newsletter', back_populates='logs')
    
    def __repr__(self):
        return f"<LogEntry(id={self.id}, level={self.level}, message={self.message[:50]}...)>"

class NewsSource(Base):
    __tablename__ = 'news_sources'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    url = Column(String(500), nullable=False)
    source_type = Column(String(50))  # web, rss, api
    is_active = Column(Boolean, default=True)
    last_scraped = Column(DateTime)
    scraping_config = Column(Text)  # JSON string with selectors, etc.
    priority = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<NewsSource(id={self.id}, name={self.name})>"

class KeywordRule(Base):
    __tablename__ = 'keyword_rules'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client = Column(String(100), nullable=False)
    section = Column(String(100), nullable=False)
    theme = Column(String(200))
    keywords = Column(Text, nullable=False)  # Pipe-separated keywords
    media_sources = Column(Text)  # Pipe-separated media sources or "Todos"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<KeywordRule(id={self.id}, client={self.client}, section={self.section})>"

# Database initialization
def init_db(database_url):
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal