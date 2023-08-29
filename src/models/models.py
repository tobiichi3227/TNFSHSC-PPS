from enum import IntEnum
from typing import Optional, List

from sqlalchemy import Column, ForeignKey, func, Sequence, DateTime, Table, JSON, Integer
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

import config


class db(object):
    pass


class Base(AsyncAttrs, DeclarativeBase):
    pass


class MemberGroup(IntEnum):
    GUEST = 0
    MEMBER = 1
    ASSOCIATION = 2  # 學生會
    SECRETARIAT = 3
    SPEAKER = 4
    ROOT = 5  #


MemberGroup.ChineseNameMap = {
    0: '訪客',
    1: '議員',
    2: '學生會',
    3: '秘書處',
    4: '議長',
    5: '超級使用者',
}


# TODO: 這個要改成IntFlag
class MemberLockReason(IntEnum):
    UnLock = 0,
    LockByPasswordReset = 1,
    LockByAdmin = 2,


MemberAndSittingsRelationship = Table("MemberAndSittingsRelationship", Base.metadata,
                                      Column("member_id", ForeignKey("Member.id"), primary_key=True),
                                      Column("sittings_id", ForeignKey("Sittings.id"), primary_key=True))

SittingAndBillRelationship = Table("SittingAndBillRelationship", Base.metadata,
                                   Column("bill_id", ForeignKey("Bill.id"), primary_key=True),
                                   Column("sittings_id", ForeignKey("Sittings.id"), primary_key=True))


class Member(Base):
    __tablename__ = 'Member'

    member_id_seq = Sequence("member_id_seq", start=1)
    id: Mapped[int] = mapped_column(member_id_seq, server_default=member_id_seq.next_value(), primary_key=True)
    class_seat_number: Mapped[int] = mapped_column(comment="班級座號")
    name: Mapped[str]
    official_name: Mapped[Optional[str]]
    mail: Mapped[str]
    password: Mapped[str]
    group: Mapped[int] = mapped_column(comment="身份組")
    is_global_constituency: Mapped[bool] = mapped_column(comment="是否為全校選區")
    appointed_dates: Mapped[int] = mapped_column(comment="屆數")
    sessions: Mapped[int] = mapped_column(comment="會期")
    permission_list: Mapped[List[int]] = mapped_column(postgresql.ARRAY(Integer))
    lock: Mapped[int] = mapped_column(default=MemberLockReason.UnLock)
    absence_records: Mapped[List["AbsenceRecord"]] = relationship(back_populates="member")
    joined_sittings: Mapped[List["Sittings"]] = relationship(secondary=MemberAndSittingsRelationship,
                                                             back_populates="participants")
    operate_logs: Mapped[List["Log"]] = relationship(backref="member")
    delete_status: Mapped[bool] = mapped_column(default=False)


class MemberConst:
    MEMBERID_GUEST = 0


class SittingType(IntEnum):
    Parpare = 0  # 預備會議
    Regular = 1  # 常會
    Extraordinary = 2  # 臨時會議
    Committee = 3  # 委員會
    Cancelled = 4  # 取消


class Sittings(Base):
    __tablename__ = 'Sittings'

    sittings_id_seq = Sequence("sittings_id_seq", start=1)
    id: Mapped[int] = mapped_column(sittings_id_seq, server_default=sittings_id_seq.next_value(), primary_key=True)
    appointed_dates: Mapped[int]
    sessions: Mapped[int]
    sitting: Mapped[int]
    sitting_type: Mapped[int]
    start_time: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True))
    location: Mapped[str] = mapped_column(comment="會議地點")
    chairperson_id: Mapped[Optional[int]] = mapped_column(ForeignKey(Member.id, onupdate="CASCADE", ondelete="CASCADE"))
    secretary_id: Mapped[Optional[int]] = mapped_column(ForeignKey(Member.id, onupdate="CASCADE", ondelete="CASCADE"))
    agenda: Mapped[Optional[str]] = mapped_column(JSON)

    participants: Mapped[List["Member"]] = relationship(back_populates="joined_sittings",
                                                        secondary=MemberAndSittingsRelationship)

    bills: Mapped[List["Bill"]] = relationship(secondary=SittingAndBillRelationship,
                                               back_populates="associate_sittings")
    delete_status: Mapped[bool] = mapped_column(default=False)


class AbsenceRecord(Base):
    __tablename__ = 'AbsenceRecord'
    absense_record_id_seq = Sequence("absence_record_id_seq", metadata=Base.metadata, start=1)
    id: Mapped[int] = mapped_column(Sequence("absence_record_id_seq", start=1),
                                    server_default=absense_record_id_seq.next_value(), primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey(Member.id, onupdate="CASCADE", ondelete="CASCADE"))
    sitting_id: Mapped[int] = mapped_column(ForeignKey(Sittings.id, onupdate="CASCADE", ondelete="CASCADE"))
    entry_time: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    exit_time: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True))
    member: Mapped[Member] = relationship(back_populates="absence_records")
    delete_status: Mapped[bool] = mapped_column(default=False)


class BillSource(IntEnum):
    Default = 0,
    Impromptu = 1,


class Bill(Base):
    __tablename__ = 'Bill'

    bill_id_seq = Sequence("bill_id_seq", start=1)
    id: Mapped[int] = mapped_column(bill_id_seq, server_default=bill_id_seq.next_value(), primary_key=True)
    name: Mapped[str]
    desc: Mapped[Optional[str]]
    data: Mapped[Optional[str]] = mapped_column(JSON)
    source: Mapped[int]

    # for tree use
    sitting_id: Mapped[Optional[int]] = mapped_column(ForeignKey(Sittings.id, onupdate="CASCADE", ondelete="CASCADE"))
    parent_id: Mapped[Optional[int]] = mapped_column(default=-1)
    root_id: Mapped[Optional[int]] = mapped_column(default=-1)

    associate_sittings: Mapped[List["Sittings"]] = relationship(secondary=SittingAndBillRelationship,
                                                                back_populates="bills")
    delete_status: Mapped[bool] = mapped_column(default=False)


class Log(Base):
    __tablename__ = 'Log'

    log_id_seq = Sequence("log_id_seq", start=1)
    id: Mapped[int] = mapped_column(log_id_seq, server_default=log_id_seq.next_value(), primary_key=True)
    operator_id: Mapped[int] = mapped_column(ForeignKey(Member.id, onupdate="CASCADE", ondelete="CASCADE"))
    timestamp: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    message: Mapped[str]
    operate_type: Mapped[str]
    params: Mapped[Optional[str]]


class SystemConfig(Base):
    __tablename__ = 'SystemConfig'

    id: Mapped[int] = mapped_column(primary_key=True)
    current_appointed_dates: Mapped[int]
    current_sessions: Mapped[int]


db.Member = Member
db.AbsenceRecord = AbsenceRecord
db.Sittings = Sittings
db.Bill = Bill
db.Log = Log
db.Sessions = async_sessionmaker()
Sessions = async_sessionmaker()


async def connect_db(db):
    print("db init")

    # db_engine = create_async_engine(
    #     f"postgresql+asyncpg://{config.DB_UESR}:{config.DB_USER_PW}@{config.DB_IP}/pps_test",
    #     echo=True, max_overflow=0, pool_size=3, pool_timeout=10, pool_recycle=1)
    db_engine = create_async_engine(
        f"postgresql+asyncpg://{config.DB_UESR}:{config.DB_USER_PW}@{config.DB_IP}/pps_test",
        max_overflow=0, pool_size=3, pool_timeout=10, pool_recycle=1)
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(db_engine)
    db.Sessions = Session
    global Sessions
    Sessions = Session


def get_session():
    return Sessions
