-- =======================================================
-- 1. DEPARTMENTS (Independent Table)
-- =======================================================
INSERT INTO Departments (department_id, name, faculty_name, budget_code, head_of_department) VALUES
(1, 'Computer Engineering', 'Faculty of Computer & Informatics', 'BUD-CS-01', 'Prof. Dr. Ali Veli'),
(2, 'Architecture', 'Faculty of Architecture', 'BUD-ARCH-01', 'Prof. Dr. Mimar Sinan');

-- =======================================================
-- 2. USERS (Columns: full_name, email, password_hash, role)
-- =======================================================
INSERT INTO Users (user_id, full_name, email, password_hash, role) VALUES
(1, 'System Admin', 'admin@itu.edu.tr', 'hashed_secret', 'Admin'),
(2, 'Ahmet Yilmaz', 'ahmet@itu.edu.tr', 'hashed_secret', 'Instructor'),
(3, 'Ayse Demir', 'ayse@itu.edu.tr', 'hashed_secret', 'Instructor'),
(4, 'Omer Atmaca', 'omer@itu.edu.tr', 'hashed_secret', 'Student'),
(5, 'Mehmet Kaya', 'mehmet@itu.edu.tr', 'hashed_secret', 'Student'),
(6, 'Zeynep Celik', 'zeynep@itu.edu.tr', 'hashed_secret', 'Student');

-- =======================================================
-- 3. PROFILES (Linked to Users and Departments)
-- =======================================================

-- Instructor Profiles
INSERT INTO Instructor_Profiles (instructor_id, department_id, title, office_location, research_interests) VALUES
(2, 1, 'Assoc. Prof.', 'EEB 404', 'Artificial Intelligence, Machine Learning'),
(3, 1, 'Assist. Prof.', 'EEB 202', 'Database Systems, Big Data');

-- Student Profiles (Column: admission_year)
INSERT INTO Student_Profiles (student_id, department_id, admission_year, current_gpa, credits_earned) VALUES
(4, 1, 2022, 3.50, 60), -- Omer (Computer Engineering)
(5, 1, 2023, 1.80, 45), -- Mehmet (Computer Engineering - Low GPA scenario)
(6, 2, 2024, 3.90, 30); -- Zeynep (Architecture)

-- =======================================================
-- 4. ACADEMIC STRUCTURE (Courses & Prerequisites)
-- =======================================================

INSERT INTO Courses (course_id, course_code, title, description, credits, department_id) VALUES
(1, 'CS101', 'Intro to Programming', 'Python programming basics', 3, 1),
(2, 'CS102', 'Data Structures', 'Arrays, Lists, Trees', 4, 1),
(3, 'CS201', 'Database Systems', 'SQL, Normalization, ER Diagrams', 3, 1),
(4, 'ARCH101', 'Design Basics', 'Introduction to architectural design', 5, 2);

-- Prerequisites
INSERT INTO Course_Prerequisites (course_id, prerequisite_id) VALUES
(2, 1); -- CS101 is required for CS102

-- =======================================================
-- 5. SECTIONS (Semester-based Classes)
-- =======================================================

INSERT INTO Course_Sections (section_id, course_id, instructor_id, semester, year, schedule_day, schedule_time, classroom, capacity) VALUES
(1, 1, 2, 'Fall', 2024, 'Monday', '09:00-12:00', 'B-101', 50),  -- CS101 (Instructor: Ahmet)
(2, 3, 3, 'Fall', 2024, 'Wednesday', '14:00-17:00', 'LAB-3', 30), -- DB (Instructor: Ayse)
(3, 4, NULL, 'Fall', 2024, 'Friday', '10:00-13:00', 'Studio-1', 25); -- Architecture (No Instructor assigned yet)

-- =======================================================
-- 6. ENROLLMENTS (Registrations & Grades)
-- =======================================================

-- Omer: Taking Database course (Ongoing)
INSERT INTO Enrollments (student_id, section_id, grade, completion_status) VALUES
(4, 2, NULL, 'Enrolled');

-- Mehmet: Taking Database course (Ongoing)
INSERT INTO Enrollments (student_id, section_id, grade, completion_status) VALUES
(5, 2, NULL, 'Enrolled');

-- PAST COURSE SCENARIO: Omer passed CS101 (Grade: AA)
INSERT INTO Enrollments (student_id, section_id, grade, completion_status) VALUES
(4, 1, 'AA', 'Completed');

-- FAILURE SCENARIO: Mehmet failed CS101 (Grade: FF)
INSERT INTO Enrollments (student_id, section_id, grade, completion_status) VALUES
(5, 1, 'FF', 'Completed');

-- CROSS-DEPARTMENT SCENARIO: Omer (Comp. Eng) taking Architecture course
INSERT INTO Enrollments (student_id, section_id, grade, completion_status) VALUES
(4, 3, NULL, 'Enrolled');

-- =======================================================
-- 7. ASSIGNMENTS & SUBMISSIONS
-- =======================================================

-- Assignments for Database Course (Section 2)
INSERT INTO Assignments (section_id, title, description, due_date, max_score, weight) VALUES
(2, 'ER Diagram Project', 'Design a library system DB', '2024-11-20 23:59:00', 100, 20.00),
(2, 'SQL Quiz', 'Basic SELECT queries', '2024-12-01 10:00:00', 50, 10.00);

-- Submissions
-- Omer submitted the project
INSERT INTO Submissions (assignment_id, student_id, file_path, score, feedback) VALUES
(1, 4, '/uploads/omer_project.pdf', 95.00, 'Great normalization work.');

-- Mehmet did not submit (No entry here, useful for testing LEFT JOIN / Missing Data)

-- =======================================================
-- 8. ATTENDANCE
-- =======================================================

INSERT INTO Attendance (section_id, student_id, attendance_date, status) VALUES
(2, 4, '2024-10-25', 'Present'), -- Omer was present
(2, 5, '2024-10-25', 'Absent');  -- Mehmet was absent

-- =======================================================
-- 9. ANNOUNCEMENTS
-- =======================================================
-- Note: 'created_by' column was removed based on your schema.

INSERT INTO Announcements (section_id, title, content) VALUES
(1, 'Class Cancellation', 'Dear students, this weeks class is cancelled due to health reasons.'),
(2, 'Midterm Date', 'The midterm exam will be held on November 25th.');

-- =======================================================
-- 10. OFFICE HOURS
-- =======================================================

INSERT INTO Office_Hours (instructor_id, day_of_week, start_time, end_time, location) VALUES
(2, 'Tuesday', '14:00:00', '16:00:00', 'EEB 404'),
(3, 'Thursday', '10:00:00', '12:00:00', 'Zoom Link: bit.ly/office');