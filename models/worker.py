# models/worker.py — Modelos do schema 'worker' (gerenciados por este backend)
from sqlalchemy import Column, Integer, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from database import Base


class Job(Base):
    """Tabela principal de jobs — cada job representa uma tarefa para o worker executar."""
    __tablename__ = "jobs"
    __table_args__ = {'schema': 'worker', 'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    carteirinha_id = Column(Integer, nullable=True)
    id_convenio = Column(Integer, nullable=True)
    rotina = Column(Text)  # op0_login, op1_consulta, op2_autorizar, etc.
    params = Column(JSONB, nullable=True)  # Todos os parâmetros para este job em JSON
    result_data = Column(JSONB, nullable=True)  # Resposta JSON do worker
    result_consumed = Column(Boolean, default=False)  # Flag: backend já consumiu o resultado?
    status = Column(Text, nullable=False, default="pending")  # pending, processing, success, error
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    priority = Column(Integer, default=0)
    depending_id = Column(Integer, ForeignKey("worker.jobs.id", ondelete="SET NULL"), nullable=True)
    locked_by = Column(Text)  # URL do servidor que está processando
    error_message = Column(Text, nullable=True)  # Última mensagem de erro
    timeout = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Log(Base):
    """Tabela de logs de execução de jobs."""
    __tablename__ = "logs"
    __table_args__ = {'schema': 'worker', 'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("worker.jobs.id", ondelete="SET NULL"), nullable=True)
    carteirinha_id = Column(Integer, nullable=True)
    user_id = Column(Integer, nullable=True, index=True)
    level = Column(Text, default="INFO")
    message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Worker(Base):
    """Tabela de workers registrados — máquinas que executam os jobs."""
    __tablename__ = "workers"
    __table_args__ = {'schema': 'worker', 'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(Text, unique=True, nullable=False)
    status = Column(Text, default="offline")  # idle, processing, offline, error
    last_heartbeat = Column(DateTime(timezone=True), server_default=func.now())
    current_job_id = Column(Integer, nullable=True)
    command = Column(Text, nullable=True)  # restart, stop
    meta = Column(Text, nullable=True)
    first_error_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class WorkerServer(Base):
    """Tabela de servidores associados a workers e usuários."""
    __tablename__ = "worker_servers"
    __table_args__ = {'schema': 'worker', 'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("worker.workers.id", ondelete="CASCADE"))
    user_id = Column(Integer, nullable=True)
    server_url = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class JobExecution(Base):
    """Tabela de execuções de jobs — histórico detalhado de cada tentativa."""
    __tablename__ = "job_executions"
    __table_args__ = {'schema': 'worker', 'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("worker.jobs.id", ondelete="CASCADE"))
    id_convenio = Column(Integer, nullable=True)
    rotina = Column(Text)
    status = Column(Text)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)
    items_found = Column(Integer, default=0)
    error_category = Column(Text)
    error_message = Column(Text)
    meta = Column(JSONB)


class ServerConfig(Base):
    """Tabela de configurações de servidores — preferências de roteamento."""
    __tablename__ = "server_configs"
    __table_args__ = {'schema': 'worker', 'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    server_url = Column(Text, unique=True, nullable=False)
    id_convenio = Column(Integer, nullable=True)
    rotina = Column(Text, nullable=True)
    preference_bonus = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PriorityRule(Base):
    """Tabela de regras de prioridade — define prioridade base e escalonamento por rotina/convênio."""
    __tablename__ = "priority_rules"
    __table_args__ = {'schema': 'worker', 'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    id_convenio = Column(Integer, nullable=True)
    rotina = Column(Text)
    base_priority = Column(Integer, default=2)
    escalation_minutes = Column(Integer, default=10)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class WorkerIntegrador(Base):
    __tablename__ = "integradores"
    __table_args__ = {'schema': 'worker', 'extend_existing': True}

    id_integrador = Column(Integer, primary_key=True, index=True)
    nome = Column(Text, nullable=False)
    sigla = Column(Text, nullable=True)
    tipo_operacao = Column(Text, default="convenio")
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class WorkerIntegradorOperacao(Base):
    __tablename__ = "integrador_operacoes"
    __table_args__ = {'schema': 'worker', 'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    id_integrador = Column(Integer, ForeignKey("worker.integradores.id_integrador", ondelete="CASCADE"), nullable=False)
    rotina = Column(Text, nullable=False)
    descricao = Column(Text, nullable=True)
    tipo_processamento = Column(Text, default="local")
    ativo = Column(Boolean, default=True)
    params_schema = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# Aliases para retrocompatibilidade
WorkerConvenio = WorkerIntegrador
WorkerConvenioOperacao = WorkerIntegradorOperacao


class WorkerConfig(Base):
    __tablename__ = "worker_config"
    __table_args__ = {'schema': 'worker', 'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    chave = Column(Text, unique=True, nullable=False)
    valor = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class WorkerApiKey(Base):
    __tablename__ = "worker_api_keys"
    __table_args__ = {'schema': 'worker', 'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    api_key = Column(Text, unique=True, nullable=False)
    user_id = Column(Integer, nullable=False)
    tipo_processamento = Column(Text, nullable=False, default="local")
    descricao = Column(Text, nullable=True)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


