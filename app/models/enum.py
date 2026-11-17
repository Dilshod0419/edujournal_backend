import enum


class RoleEnum(str, enum.Enum):
    admin = "admin"
    teacher = "teacher"
    pupil = "pupil"


class AttendanceStatus(str, enum.Enum):
    present = "present"   # keldi
    absent = "absent"     # kelmadi
    late = "late"         # kech qoldi
    excused = "excused"   # sababli
