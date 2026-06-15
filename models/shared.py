# models/shared.py — Modelos do schema 'public' (gerenciados pelo backend principal, somente leitura aqui)
from sqlalchemy import Column, Integer, Text, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.sql import func

from database import Base


class User(Base):
    """Tabela de usuários — gerenciada pelo backend principal."""
    __tablename__ = "users"
    __table_args__ = {'schema': 'public', 'extend_existing': True}

    id = Column(Integer, primary_key=True)
    username = Column(Text, nullable=False)
    api_key = Column(Text, unique=True, nullable=False)
    validade = Column(Date)
    status = Column(Text, default="Ativo")
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class Convenio(Base):
    """Tabela de convênios disponíveis."""
    __tablename__ = "convenios"
    __table_args__ = {'schema': 'public', 'extend_existing': True}

    id_convenio = Column(Integer, primary_key=True)
    nome = Column(Text, nullable=False)


class UserConvenio(Base):
    """Tabela de vínculo entre usuários e convênios, com credenciais."""
    __tablename__ = "user_convenios"
    __table_args__ = {'schema': 'public', 'extend_existing': True}

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("public.users.id"))
    id_convenio = Column(Integer, ForeignKey("public.convenios.id_convenio"))
    login = Column(Text, nullable=True)
    senha_criptografada = Column(Text, nullable=True)
    cod_prestador = Column(Text, nullable=True)
    login_fat = Column(Text, nullable=True)
    senha_fat_criptografada = Column(Text, nullable=True)


class ConvenioOperacao(Base):
    """Tabela de operações disponíveis por convênio."""
    __tablename__ = "convenio_operacoes"
    __table_args__ = {'schema': 'public', 'extend_existing': True}

    id = Column(Integer, primary_key=True)
    id_convenio = Column(Integer, ForeignKey("public.convenios.id_convenio"))
    descricao = Column(Text, nullable=False)
    valor = Column(Text, nullable=False)


class Carteirinha(Base):
    """Tabela de carteirinhas de pacientes."""
    __tablename__ = "carteirinhas"
    __table_args__ = {'schema': 'public', 'extend_existing': True}

    id = Column(Integer, primary_key=True)
    carteirinha = Column(Text, nullable=False)
    paciente = Column(Text)
    id_convenio = Column(Integer, ForeignKey("public.convenios.id_convenio"))
    user_id = Column(Integer, ForeignKey("public.users.id"))
    codigo_beneficiario = Column(Text, nullable=True)
