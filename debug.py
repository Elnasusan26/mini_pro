# from models import db, Class, Subject, TimetableEntry, TeachingAssignment
# from utils.normalize import normalize_slot
# import random
# from input_processor import PARALLEL_DATA, SUBJECT_REQUIREMENTS

# DAYS = [
#     "MONDAY", "TUESDAY", "WEDNESDAY",
#     "THURSDAY", "FRIDAY", "SATURDAY"
# ]

# TIME_SLOTS = list(map(normalize_slot, [
#     "8.00-8.45",
#     "9.10-9.55",
#     "10.00-10.45",
#     "10.50-11.35",
#     "11.55-12.40",
#     "12.45-1.30"
# ]))


# def generate_timetable():
#     print("⚡ Generating timetable...")

#     TimetableEntry.query.delete()
#     db.session.commit()

#     classes = Class.query.all()

#     for cls in classes:

#         assignments = TeachingAssignment.query.filter_by(class_id=cls.id).all()

#         tasks = []
#         lab_tasks = []

#         # 🔥 STEP 1: GROUP SUBJECTS
#         subject_map = {}
#         for a in assignments:
#             subject_map.setdefault(a.subject_id, []).append(a)

#         # 🔥 STEP 2: SPLIT LAB & THEORY
#         for subject_id, teachers in subject_map.items():

#             hours = SUBJECT_REQUIREMENTS.get(
#                 cls.id, {}).get(subject_id, teachers[0].hours_per_week
#             )

#             subject = Subject.query.get(subject_id)

#             if subject and subject.is_lab:
#                 lab_tasks.append({
#                     "class_id": cls.id,
#                     "subject_id": subject_id,
#                     "teacher_ids": [t.teacher_id for t in teachers],
#                     "hours": hours
#                 })
#             else:
#                 for _ in range(hours):
#                     tasks.append({
#                         "class_id": cls.id,
#                         "subject_id": subject_id,
#                         "teacher_id": random.choice(teachers).teacher_id
#                     })

#         # 🔥 STEP 3: LAB ASSIGNMENT
#         for lab in lab_tasks:

#             remaining_hours = lab["hours"]

#             for day in DAYS:

#                 if remaining_hours <= 0:
#                     break

#                 existing_lab = TimetableEntry.query.join(Subject).filter(
#                     TimetableEntry.class_id == cls.id,
#                     TimetableEntry.day == day,
#                     Subject.is_lab == True
#                 ).first()

#                 if existing_lab:
#                     continue

#                 # block size
#                 block_size = 3 if remaining_hours >= 3 else remaining_hours

#                 for i in range(len(TIME_SLOTS) - (block_size - 1)):

#                     slots = TIME_SLOTS[i:i+block_size]
#                     selected_teacher = None

#                     # pick one teacher
#                     for t_id in lab["teacher_ids"]:
#                         if all(not TimetableEntry.query.filter_by(
#                                 teacher_id=t_id, day=day, slot=s).first()
#                                for s in slots):
#                             selected_teacher = t_id
#                             break

#                     if not selected_teacher:
#                         continue

#                     # class conflict
#                     if any(TimetableEntry.query.filter_by(
#                             class_id=cls.id, day=day, slot=s).first()
#                            for s in slots):
#                         continue

#                     for s in slots:
#                         db.session.add(TimetableEntry(
#                             class_id=cls.id,
#                             subject_id=lab["subject_id"],
#                             teacher_id=selected_teacher,
#                             day=day,
#                             slot=s,
#                             is_lab_hour=True
#                         ))

#                     remaining_hours -= block_size
#                     break

#         # 🔥 STEP 4: THEORY (SKIP SATURDAY FOR S8_CSE)
#         random.shuffle(tasks)

#         for task in tasks:
#             placed = False

#             for day in DAYS:

#                 # 🚨 SKIP SATURDAY
#                 if cls.name == "S8_CSE" and day == "SATURDAY":
#                     continue

#                 for slot in TIME_SLOTS:

#                     if TimetableEntry.query.filter_by(
#                         class_id=cls.id, day=day, slot=slot
#                     ).first():
#                         continue

#                     if TimetableEntry.query.filter_by(
#                         teacher_id=task["teacher_id"], day=day, slot=slot
#                     ).first():
#                         continue

#                     db.session.add(TimetableEntry(
#                         class_id=cls.id,
#                         subject_id=task["subject_id"],
#                         teacher_id=task["teacher_id"],
#                         day=day,
#                         slot=slot
#                     ))

#                     placed = True
#                     break

#                 if placed:
#                     break

#         # 🔥 STEP 5: FORCE SATURDAY PROJECT (FINAL FIX)
#         if cls.name == "S8_CSE":

#             # ❌ CLEAR SATURDAY
#             TimetableEntry.query.filter_by(
#                 class_id=cls.id,
#                 day="SATURDAY"
#             ).delete()

#             db.session.commit()

#             project_subject = Subject.query.filter(
#                 Subject.name.ilike("%project%")
#             ).first()

#             if project_subject:

#                 project_teachers = subject_map.get(project_subject.id, [])

#                 for slot in TIME_SLOTS:

#                     selected_teacher = None

#                     for t in project_teachers:
#                         if not TimetableEntry.query.filter_by(
#                             teacher_id=t.teacher_id,
#                             day="SATURDAY",
#                             slot=slot
#                         ).first():
#                             selected_teacher = t.teacher_id
#                             break

#                     if not selected_teacher and project_teachers:
#                         selected_teacher = random.choice(project_teachers).teacher_id

#                     if selected_teacher:
#                         db.session.add(TimetableEntry(
#                             class_id=cls.id,
#                             subject_id=project_subject.id,
#                             teacher_id=selected_teacher,
#                             day="SATURDAY",
#                             slot=slot
#                         ))

#         # 🔥 STEP 6: FILL REMAINING
#         day_subject_count = {}

#         for day in DAYS:
#             for slot in TIME_SLOTS:

#                 if cls.name == "S8_CSE" and day == "SATURDAY":
#                     continue

#                 if TimetableEntry.query.filter_by(
#                     class_id=cls.id, day=day, slot=slot
#                 ).first():
#                     continue

#                 for subject_id, teachers in subject_map.items():

#                     subject = Subject.query.get(subject_id)

#                     if subject and subject.is_lab:
#                         continue

#                     count = day_subject_count.get((day, subject_id), 0)
#                     if count >= 2:
#                         continue

#                     teacher_id = random.choice(teachers).teacher_id

#                     if TimetableEntry.query.filter_by(
#                         teacher_id=teacher_id, day=day, slot=slot
#                     ).first():
#                         continue

#                     db.session.add(TimetableEntry(
#                         class_id=cls.id,
#                         subject_id=subject_id,
#                         teacher_id=teacher_id,
#                         day=day,
#                         slot=slot
#                     ))

#                     day_subject_count[(day, subject_id)] = count + 1
#                     break

#         # 🔥 STEP 7: PARALLEL
#         if cls.id in PARALLEL_DATA:
#             for pc in PARALLEL_DATA[cls.id]:

#                 existing = TimetableEntry.query.filter_by(
#                     class_id=cls.id,
#                     day=pc["day"],
#                     slot=pc["slot"]
#                 ).first()

#                 if existing:
#                     assignment = TeachingAssignment.query.filter_by(
#                         class_id=cls.id,
#                         subject_id=pc["subject_id"]
#                     ).first()

#                     existing.subject_id = pc["subject_id"]
#                     existing.teacher_id = (
#                         assignment.teacher_id if assignment else None
#                     )
#                     existing.batch = pc["batch"]
#                     existing.is_floating = True

#     db.session.commit()
#     print("✅ Timetable generated!")