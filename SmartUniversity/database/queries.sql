USE smart_university;


SELECT * FROM Users;





-- ==========================================
-- 1. LOGIN & AUTH (Giriş Simülasyonu)
-- ==========================================

-- Senaryo: Kullanıcı email ve şifresini girdi. Sistemde var mı?
-- Beklenen: Ömer'in bilgilerini getirmeli.
SELECT user_id, full_name, role, password_hash 
FROM Users 
WHERE email = 'omer@itu.edu.tr';


-- ==========================================
-- 2. ÖĞRENCİ EKRANI (Student Dashboard)
-- ==========================================

-- Senaryo: Ömer (ID: 4) sisteme girdi. Şu an aldığı dersleri listele.
-- Beklenen: Database Systems (Section 2) ve Mimarlık Dersi (Section 3) gelmeli.
SELECT 
    c.course_code, 
    c.title, 
    s.schedule_day, 
    s.schedule_time, 
    s.classroom,
    u.full_name as instructor_name
FROM Enrollments e
JOIN Course_Sections s ON e.section_id = s.section_id
JOIN Courses c ON s.course_id = c.course_id
LEFT JOIN Users u ON s.instructor_id = u.user_id
WHERE e.student_id = 4 AND e.completion_status = 'Enrolled';


-- Senaryo: Ömer transkriptini (geçmiş derslerini) görmek istiyor.
-- Beklenen: CS101 (AA) gelmeli.
SELECT 
    c.course_code, 
    c.title, 
    e.grade, 
    e.completion_status
FROM Enrollments e
JOIN Course_Sections s ON e.section_id = s.section_id
JOIN Courses c ON s.course_id = c.course_id
WHERE e.student_id = 4 AND e.completion_status = 'Completed';


-- ==========================================
-- 3. HOCA EKRANI (Instructor Dashboard)
-- ==========================================

-- Senaryo: Ayşe Hoca (ID: 3) "Database Systems" (Section ID: 2) dersini veriyor.
-- Sınıf listesini (Roster) görmek istiyor.
-- Beklenen: Ömer ve Mehmet listelenmeli.
SELECT 
    u.full_name, 
    u.email, 
    sp.admission_year
FROM Enrollments e
JOIN Users u ON e.student_id = u.user_id
JOIN Student_Profiles sp ON u.user_id = sp.student_id
WHERE e.section_id = 2;


-- Senaryo: Ayşe Hoca, verilen ödevlerin (Assignment ID: 1) durumunu görmek istiyor.
-- ÖNEMLİ: Teslim etmeyenleri de görmek istiyor (LEFT JOIN kullanımı).
-- Beklenen: Ömer -> Dosya yolu var, Puanı var. Mehmet -> NULL (Teslim etmedi).
SELECT 
    u.full_name, 
    s.submission_date, 
    s.file_path, 
    s.score 
FROM Enrollments e
JOIN Users u ON e.student_id = u.user_id
LEFT JOIN Submissions s ON e.student_id = s.student_id AND s.assignment_id = 1
WHERE e.section_id = 2; -- Database Dersi Section ID'si


-- ==========================================
-- 4. ANALİTİK & RAPORLAR (Complex Queries)
-- ==========================================

-- Senaryo: Bölümü dışından ders alan öğrencileri bul (Çapraz Disiplin).
-- Mantık: Öğrencinin bölümü (Student_Profile) ile Dersin bölümü (Courses) farklıysa getir.
-- Beklenen: Ömer (CS) -> Architecture dersi alıyor.
SELECT 
    u.full_name, 
    std_dept.name AS student_department,
    c.title AS course_taken,
    crs_dept.name AS course_department
FROM Enrollments e
JOIN Users u ON e.student_id = u.user_id
JOIN Student_Profiles sp ON u.user_id = sp.student_id
JOIN Departments std_dept ON sp.department_id = std_dept.department_id
JOIN Course_Sections s ON e.section_id = s.section_id
JOIN Courses c ON s.course_id = c.course_id
JOIN Departments crs_dept ON c.department_id = crs_dept.department_id
WHERE sp.department_id != c.department_id;


-- Senaryo: Devamsızlık Analizi. Kimler devamsız (Absent) veya geç (Late)?
-- Beklenen: Mehmet (Absent)
SELECT 
    u.full_name, 
    c.title, 
    a.attendance_date, 
    a.status
FROM Attendance a
JOIN Users u ON a.student_id = u.user_id
JOIN Course_Sections s ON a.section_id = s.section_id
JOIN Courses c ON s.course_id = c.course_id
WHERE a.status IN ('Absent', 'Late');