USE smart_university;

CREATE TABLE Users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,        
    full_name VARCHAR(100) NOT NULL,               -- 
    email VARCHAR(100) NOT NULL UNIQUE,            -- 
    password_hash VARCHAR(255) NOT NULL,           -- 
    role ENUM('Student', 'Instructor', 'Admin') NOT NULL, -- 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 
    is_active BOOLEAN DEFAULT TRUE                 --  (soft delete)
)ENGINE=InnoDB;

CREATE TABLE Departments (
    department_id INT PRIMARY KEY,   -- Departmen IDs are not auto incremented
    name VARCHAR(100) NOT NULL UNIQUE,      -- "Computer Engineering"
    faculty_name VARCHAR(100) NOT NULL, -- "Faculty of Computer & Informatics"
    budget_code VARCHAR(50),         
    head_of_department VARCHAR(100)  
)ENGINE=InnoDB;

CREATE TABLE Student_Profiles (
    student_id INT PRIMARY KEY,
    department_id INT NOT NULL,
    admission_year YEAR,
    current_gpa DECIMAL(3,2) DEFAULT 0.00,
    credits_earned INT DEFAULT 0,
    
    FOREIGN KEY (student_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (department_id) REFERENCES Departments(department_id),
	
    CONSTRAINT chk_gpa CHECK (current_gpa >= 0.00 AND current_gpa <= 4.00),
    CONSTRAINT chk_credits CHECK (credits_earned >= 0 AND credits_earned <= 400) 
)ENGINE=InnoDB;

CREATE TABLE Instructor_Profiles (
    instructor_id INT PRIMARY KEY,
    department_id INT NOT NULL,
    title VARCHAR(50) NOT NULL,    -- "Prof. Dr.", "Assist. Prof."
    office_location VARCHAR(100),  -- "Building A, Room 304"
    research_interests TEXT,       
    
    FOREIGN KEY (instructor_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (department_id) REFERENCES Departments(department_id)
) ENGINE=InnoDB;

CREATE TABLE Courses (
    course_id INT AUTO_INCREMENT PRIMARY KEY,
    course_code VARCHAR(20) NOT NULL UNIQUE,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    credits INT NOT NULL DEFAULT 3,
    department_id INT NOT NULL,

    FOREIGN KEY (department_id) REFERENCES Departments(department_id) ON DELETE CASCADE,
    CONSTRAINT chk_course_credits CHECK (credits > 0 AND credits <= 10)
) ENGINE=InnoDB;


CREATE TABLE Course_Prerequisites (
    course_id INT NOT NULL,          
    prerequisite_id INT NOT NULL,    
    
    PRIMARY KEY (course_id, prerequisite_id),
    
    FOREIGN KEY (course_id) REFERENCES Courses(course_id) ON DELETE CASCADE,
    FOREIGN KEY (prerequisite_id) REFERENCES Courses(course_id) ON DELETE CASCADE,
    
    CONSTRAINT chk_no_self_prereq CHECK (course_id <> prerequisite_id)
) ENGINE=InnoDB;


CREATE TABLE Course_Sections (
    section_id INT AUTO_INCREMENT PRIMARY KEY,
    course_id INT NOT NULL,
    instructor_id INT,             
    semester ENUM('Fall', 'Spring', 'Summer') NOT NULL, 
    year YEAR NOT NULL,           
    schedule_day VARCHAR(15),      -- "Monday"
    schedule_time VARCHAR(20),     -- "09:00-11:50"
    classroom VARCHAR(50),         -- "B-204"
    capacity INT NOT NULL DEFAULT 40, -- Kontenjan
    
    FOREIGN KEY (course_id) REFERENCES Courses(course_id) ON DELETE CASCADE,
    FOREIGN KEY (instructor_id) REFERENCES Users(user_id) ON DELETE SET NULL,  -- if instuctor leaves,
																			   -- dont delete course
    
    CONSTRAINT chk_capacity CHECK (capacity > 0)
) ENGINE=InnoDB;

CREATE TABLE Enrollments (
    enrollment_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    section_id INT NOT NULL,
	enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
    grade VARCHAR(2), -- 'AA', 'BA', 'FF' 
    completion_status ENUM('Enrolled', 'Completed', 'Dropped', 'Failed') DEFAULT 'Enrolled',
    FOREIGN KEY (student_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (section_id) REFERENCES Course_Sections(section_id) ON DELETE CASCADE,
    
    UNIQUE (student_id, section_id)
) ENGINE=InnoDB;

CREATE TABLE Assignments (
    assignment_id INT AUTO_INCREMENT PRIMARY KEY,
    section_id INT NOT NULL,     
    
    title VARCHAR(100) NOT NULL, 
    description TEXT,           
    due_date DATETIME NOT NULL,  
    
    max_score INT NOT NULL DEFAULT 100, 
    weight DECIMAL(5,2),         
    
    FOREIGN KEY (section_id) REFERENCES Course_Sections(section_id) ON DELETE CASCADE
    
) ENGINE=InnoDB;

CREATE TABLE Submissions (
    submission_id INT AUTO_INCREMENT PRIMARY KEY,
    assignment_id INT NOT NULL,
    student_id INT NOT NULL,
    submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
    file_path VARCHAR(255),  
    submission_text TEXT,   
    score DECIMAL(5,2),      
    feedback TEXT,           
    
    FOREIGN KEY (assignment_id) REFERENCES Assignments(assignment_id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    
    UNIQUE (assignment_id, student_id)
    
) ENGINE=InnoDB;


CREATE TABLE Attendance (
    attendance_id INT AUTO_INCREMENT PRIMARY KEY,
    section_id INT NOT NULL,      
    student_id INT NOT NULL,      
    
    attendance_date DATE NOT NULL, -- Dersin yapıldığı tarih
    
    status ENUM('Present', 'Absent', 'Late', 'Excused') NOT NULL DEFAULT 'Absent',
    
    FOREIGN KEY (section_id) REFERENCES Course_Sections(section_id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    
    UNIQUE (section_id, student_id, attendance_date)

) ENGINE=InnoDB;


CREATE TABLE Announcements (
    announcement_id INT AUTO_INCREMENT PRIMARY KEY,
    section_id INT NOT NULL,        
    
    title VARCHAR(150) NOT NULL,   
    content TEXT NOT NULL,         
    
    publish_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
    
	FOREIGN KEY (section_id) REFERENCES Course_Sections(section_id) ON DELETE CASCADE
    
) ENGINE=InnoDB;

CREATE TABLE Office_Hours (
    office_hour_id INT AUTO_INCREMENT PRIMARY KEY,
    instructor_id INT NOT NULL,
    
    day_of_week ENUM('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday') NOT NULL,
    start_time TIME NOT NULL,  -- 14:30:00
    end_time TIME NOT NULL,    -- 16:30:00
    
    location VARCHAR(100),     
    
    -- İLİŞKİLER
    FOREIGN KEY (instructor_id) REFERENCES Users(user_id) ON DELETE CASCADE
    
) ENGINE=InnoDB;