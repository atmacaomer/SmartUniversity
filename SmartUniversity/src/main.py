from fastapi import FastAPI
from .routers import (
    auth,
    users,
    students_profiles,
    instructors_profiles,
    departments,
    courses,
    prerequisites,
    course_sections,
    enrollments,
    assignments,
    submissions,
    attendance,
    office_hours,
    announcements,
    analytics
)

app = FastAPI(
    title="University Database API",
    description="A comprehensive REST API for managing university operations.",
    version="1.0.0"
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(departments.router)
app.include_router(students_profiles.router)
app.include_router(instructors_profiles.router)
app.include_router(courses.router)
app.include_router(prerequisites.router)
app.include_router(course_sections.router)
app.include_router(enrollments.router)
app.include_router(assignments.router)
app.include_router(submissions.router)
app.include_router(attendance.router)
app.include_router(office_hours.router)
app.include_router(announcements.router)
app.include_router(analytics.router)

@app.get("/")
def root():
    return {"message": "Welcome to the University Database API. Go to /docs to see the documentation."}