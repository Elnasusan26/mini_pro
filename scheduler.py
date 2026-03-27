from models import db, Class, Subject, TimetableEntry, TeachingAssignment
from utils.normalize import normalize_slot
import random
from input_processor import PARALLEL_DATA, SUBJECT_REQUIREMENTS

DAYS = [
    "MONDAY", "TUESDAY", "WEDNESDAY",
    "THURSDAY", "FRIDAY", "SATURDAY"
]

TIME_SLOTS = list(map(normalize_slot, [
    "8.00-8.45",
    "9.10-9.55",
    "10.00-10.45",
    "10.50-11.35",
    "11.55-12.40",
    "12.45-1.30"
]))


def generate_timetable():
    print("⚡ Generating timetable...")

    TimetableEntry.query.delete()
    db.session.commit()

    classes = Class.query.all()

    for cls in classes:

        assignments = TeachingAssignment.query.filter_by(class_id=cls.id).all()

        tasks = []
        lab_tasks = []

        # 🔥 STEP 1: SPLIT LAB & THEORY
        for a in assignments:
            hours = SUBJECT_REQUIREMENTS.get(
                cls.id, {}).get(a.subject_id, a.hours_per_week)

            subject = Subject.query.get(a.subject_id)

            if subject and subject.is_lab:
                lab_tasks.append({
                    "class_id": cls.id,
                    "subject_id": a.subject_id,
                    "teacher_id": a.teacher_id,
                    "hours": min(hours, 6)
                })
            else:
                for _ in range(hours):
                    tasks.append({
                        "class_id": cls.id,
                        "subject_id": a.subject_id,
                        "teacher_id": a.teacher_id
                    })

        # 🔥 STEP 2: LABS (CONSECUTIVE)
        for lab in lab_tasks:

            remaining_hours = lab["hours"]

            for day in DAYS:

                if remaining_hours <= 0:
                    break

                existing_lab = TimetableEntry.query.join(Subject).filter(
                    TimetableEntry.class_id == cls.id,
                    TimetableEntry.day == day,
                    Subject.is_lab == True
                ).first()

                if existing_lab:
                    continue

                block_size = 3 if remaining_hours >= 3 else 2

                for i in range(len(TIME_SLOTS) - (block_size - 1)):

                    slots = TIME_SLOTS[i:i+block_size]
                    can_place = True

                    for slot in slots:

                        conflict = TimetableEntry.query.filter_by(
                            class_id=cls.id,
                            day=day,
                            slot=slot
                        ).first()

                        teacher_conflict = TimetableEntry.query.filter_by(
                            teacher_id=lab["teacher_id"],
                            day=day,
                            slot=slot
                        ).first()

                        if conflict or teacher_conflict:
                            can_place = False
                            break

                    if can_place:
                        for slot in slots:
                            db.session.add(TimetableEntry(
                                class_id=lab["class_id"],
                                subject_id=lab["subject_id"],
                                teacher_id=lab["teacher_id"],
                                day=day,
                                slot=slot,
                                is_lab_hour=True
                            ))

                        remaining_hours -= block_size
                        break

        # 🔥 STEP 3: THEORY (BALANCED DISTRIBUTION)
        random.shuffle(tasks)

        task_index = 0
        total_tasks = len(tasks)

        for slot in TIME_SLOTS:
            for day in DAYS:

                if task_index >= total_tasks:
                    break

                task = tasks[task_index]

                existing_class = TimetableEntry.query.filter_by(
                    class_id=cls.id,
                    day=day,
                    slot=slot
                ).first()

                existing_teacher = TimetableEntry.query.filter_by(
                    teacher_id=task["teacher_id"],
                    day=day,
                    slot=slot
                ).first()

                if not existing_class and not existing_teacher:

                    db.session.add(TimetableEntry(
                        class_id=task["class_id"],
                        subject_id=task["subject_id"],
                        teacher_id=task["teacher_id"],
                        day=day,
                        slot=slot
                    ))

                    task_index += 1

            if task_index >= total_tasks:
                break

        # 🔥 STEP 4: FILL EMPTY SLOTS
        for day in DAYS:
            for slot in TIME_SLOTS:

                existing = TimetableEntry.query.filter_by(
                    class_id=cls.id,
                    day=day,
                    slot=slot
                ).first()

                if existing:
                    continue

                for a in assignments:

                    subject = Subject.query.get(a.subject_id)

                    if subject and subject.is_lab:
                        continue

                    teacher_busy = TimetableEntry.query.filter_by(
                        teacher_id=a.teacher_id,
                        day=day,
                        slot=slot
                    ).first()

                    if teacher_busy:
                        continue

                    count = TimetableEntry.query.filter_by(
                        class_id=cls.id,
                        day=day,
                        subject_id=a.subject_id
                    ).count()

                    if count >= 3:
                        continue

                    db.session.add(TimetableEntry(
                        class_id=cls.id,
                        subject_id=a.subject_id,
                        teacher_id=a.teacher_id,
                        day=day,
                        slot=slot
                    ))

                    break

        # 🔥 STEP 5: PARALLEL CLASSES
        if cls.id in PARALLEL_DATA:
            for pc in PARALLEL_DATA[cls.id]:

                existing = TimetableEntry.query.filter_by(
                    class_id=cls.id,
                    day=pc["day"],
                    slot=pc["slot"]
                ).first()

                if existing:
                    assignment = TeachingAssignment.query.filter_by(
                        class_id=cls.id,
                        subject_id=pc["subject_id"]
                    ).first()

                    existing.subject_id = pc["subject_id"]
                    existing.teacher_id = (
                        assignment.teacher_id if assignment else None
                    )
                    existing.batch = pc["batch"]
                    existing.is_floating = True

    db.session.commit()
    print("✅ Timetable generated!")