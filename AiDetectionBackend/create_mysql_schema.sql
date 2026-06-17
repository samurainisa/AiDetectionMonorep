-- Создание базы данных для системы AI детекции и антиплагиата
CREATE DATABASE IF NOT EXISTS ai_detection_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ai_detection_system;

-- Таблица ролей
CREATE TABLE roles (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица групп/курсов
CREATE TABLE groups_courses (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    course_code VARCHAR(50),
    academic_year VARCHAR(20),
    semester INT,
    faculty VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_course_code (course_code),
    INDEX idx_academic_year (academic_year)
);

-- Таблица пользователей
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    middle_name VARCHAR(100),
    role_id INT NOT NULL,
    student_id VARCHAR(50), -- для студентов
    employee_id VARCHAR(50), -- для преподавателей
    group_id INT, -- для студентов
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (role_id) REFERENCES roles(id),
    FOREIGN KEY (group_id) REFERENCES groups_courses(id),
    INDEX idx_email (email),
    INDEX idx_role (role_id),
    INDEX idx_student_id (student_id),
    INDEX idx_group (group_id)
);

-- Таблица категорий документов
CREATE TABLE document_categories (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица детекций AI (расширенная версия текущей)
CREATE TABLE ai_detections (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    filename VARCHAR(500) NOT NULL,
    original_filename VARCHAR(500) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size BIGINT,
    file_hash VARCHAR(64), -- для дедупликации
    text_length INT NOT NULL,
    extracted_text LONGTEXT NOT NULL,
    
    -- AI детекция
    api_endpoint VARCHAR(50) NOT NULL,
    ai_likelihood DECIMAL(5,4),
    max_ai_likelihood DECIMAL(5,4),
    avg_ai_likelihood DECIMAL(5,4),
    prediction VARCHAR(100),
    fraction_ai_content DECIMAL(5,4),
    full_response JSON,
    
    -- Метаданные
    document_category_id INT,
    assignment_name VARCHAR(200),
    subject VARCHAR(100),
    is_public BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (document_category_id) REFERENCES document_categories(id),
    INDEX idx_user (user_id),
    INDEX idx_file_hash (file_hash),
    INDEX idx_created_at (created_at),
    INDEX idx_ai_likelihood (ai_likelihood),
    INDEX idx_prediction (prediction),
    INDEX idx_subject (subject)
);

-- Таблица для хранения текстовых фрагментов (для антиплагиата)
CREATE TABLE text_fragments (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    detection_id INT NOT NULL,
    fragment_text TEXT NOT NULL,
    fragment_hash VARCHAR(64) NOT NULL,
    start_position INT,
    end_position INT,
    word_count INT,
    
    -- Векторное представление (для семантического поиска)
    embedding_vector JSON, -- или BLOB для бинарных векторов
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (detection_id) REFERENCES ai_detections(id) ON DELETE CASCADE,
    INDEX idx_detection (detection_id),
    INDEX idx_fragment_hash (fragment_hash),
    INDEX idx_word_count (word_count)
);

-- Таблица совпадений для антиплагиата
CREATE TABLE plagiarism_matches (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    source_detection_id INT NOT NULL,
    target_detection_id INT NOT NULL,
    source_fragment_id BIGINT NOT NULL,
    target_fragment_id BIGINT NOT NULL,
    
    similarity_score DECIMAL(5,4) NOT NULL,
    match_type ENUM('exact', 'near_exact', 'paraphrase', 'semantic') NOT NULL,
    match_length INT, -- количество совпадающих слов
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (source_detection_id) REFERENCES ai_detections(id),
    FOREIGN KEY (target_detection_id) REFERENCES ai_detections(id),
    FOREIGN KEY (source_fragment_id) REFERENCES text_fragments(id),
    FOREIGN KEY (target_fragment_id) REFERENCES text_fragments(id),
    
    INDEX idx_source_detection (source_detection_id),
    INDEX idx_target_detection (target_detection_id),
    INDEX idx_similarity (similarity_score),
    INDEX idx_match_type (match_type),
    
    -- Уникальность пары фрагментов
    UNIQUE KEY unique_fragment_pair (source_fragment_id, target_fragment_id)
);

-- Таблица отчетов по плагиату
CREATE TABLE plagiarism_reports (
    id INT PRIMARY KEY AUTO_INCREMENT,
    detection_id INT NOT NULL,
    total_similarity_score DECIMAL(5,4),
    unique_matches_count INT DEFAULT 0,
    total_matched_words INT DEFAULT 0,
    report_data JSON, -- детальная информация о совпадениях
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (detection_id) REFERENCES ai_detections(id),
    INDEX idx_detection (detection_id),
    INDEX idx_similarity_score (total_similarity_score)
);

-- Таблица для аналитики и статистики
CREATE TABLE analytics_sessions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    session_date DATE NOT NULL,
    documents_analyzed INT DEFAULT 0,
    avg_ai_likelihood DECIMAL(5,4),
    plagiarism_cases_found INT DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user_date (user_id, session_date),
    INDEX idx_session_date (session_date)
);

-- Таблица настроек системы
CREATE TABLE system_settings (
    id INT PRIMARY KEY AUTO_INCREMENT,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Таблица логов действий пользователей
CREATE TABLE user_activity_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INT,
    details JSON,
    ip_address VARCHAR(45),
    user_agent TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user_action (user_id, action),
    INDEX idx_created_at (created_at)
);

-- Заполнение базовых данных
INSERT INTO roles (name, description) VALUES 
('student', 'Студент'),
('teacher', 'Преподаватель'),
('admin', 'Администратор системы');

INSERT INTO document_categories (name, description) VALUES 
('coursework', 'Курсовая работа'),
('essay', 'Эссе'),
('report', 'Отчет'),
('thesis', 'Дипломная работа'),
('homework', 'Домашнее задание'),
('other', 'Другое');

INSERT INTO system_settings (setting_key, setting_value, description) VALUES
('plagiarism_threshold', '0.15', 'Порог схожести для определения плагиата'),
('ai_detection_threshold', '0.7', 'Порог AI детекции'),
('max_file_size', '16777216', 'Максимальный размер файла в байтах'),
('fragment_min_words', '10', 'Минимальное количество слов во фрагменте'),
('fragment_max_words', '50', 'Максимальное количество слов во фрагменте');

-- Создание индексов для оптимизации аналитических запросов
CREATE INDEX idx_ai_detections_analytics ON ai_detections(user_id, created_at, ai_likelihood, prediction);
CREATE INDEX idx_plagiarism_analytics ON plagiarism_matches(source_detection_id, similarity_score, match_type);
CREATE INDEX idx_user_group_analytics ON users(group_id, role_id, is_active);

-- Представления для аналитики
CREATE VIEW user_statistics AS
SELECT 
    u.id as user_id,
    u.first_name,
    u.last_name,
    u.email,
    r.name as role,
    gc.name as group_name,
    COUNT(ad.id) as total_documents,
    AVG(ad.ai_likelihood) as avg_ai_likelihood,
    COUNT(CASE WHEN ad.ai_likelihood > 0.7 THEN 1 END) as high_ai_documents,
    COUNT(pr.id) as plagiarism_reports_count
FROM users u
LEFT JOIN roles r ON u.role_id = r.id
LEFT JOIN groups_courses gc ON u.group_id = gc.id
LEFT JOIN ai_detections ad ON u.id = ad.user_id
LEFT JOIN plagiarism_reports pr ON ad.id = pr.detection_id
GROUP BY u.id, u.first_name, u.last_name, u.email, r.name, gc.name;

CREATE VIEW group_analytics AS
SELECT 
    gc.id as group_id,
    gc.name as group_name,
    gc.course_code,
    gc.academic_year,
    COUNT(DISTINCT u.id) as students_count,
    COUNT(ad.id) as total_documents,
    AVG(ad.ai_likelihood) as avg_ai_likelihood,
    COUNT(CASE WHEN ad.ai_likelihood > 0.7 THEN 1 END) as high_ai_documents,
    COUNT(pr.id) as plagiarism_cases
FROM groups_courses gc
LEFT JOIN users u ON gc.id = u.group_id AND u.role_id = (SELECT id FROM roles WHERE name = 'student')
LEFT JOIN ai_detections ad ON u.id = ad.user_id
LEFT JOIN plagiarism_reports pr ON ad.id = pr.detection_id
GROUP BY gc.id, gc.name, gc.course_code, gc.academic_year;

-- Обновленная схема базы данных для AI Detection с расширенными признаками
-- Версия: 2.0

CREATE TABLE IF NOT EXISTS detection (
    id INT AUTO_INCREMENT PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    text_length INT NOT NULL,
    extracted_text LONGTEXT NOT NULL,
    api_endpoint VARCHAR(50) NOT NULL,
    ai_likelihood FLOAT NULL,
    max_ai_likelihood FLOAT NULL,
    avg_ai_likelihood FLOAT NULL,
    prediction VARCHAR(100) NULL,
    fraction_ai_content FLOAT NULL,
    full_response LONGTEXT NOT NULL,
    
    -- Расширенные признаки (статистические)
    word_count INT NULL,
    sentence_count INT NULL,
    paragraph_count INT NULL,
    avg_word_length FLOAT NULL,
    avg_sentence_length FLOAT NULL,
    sentence_length_variance FLOAT NULL,
    punctuation_density FLOAT NULL,
    uppercase_ratio FLOAT NULL,
    
    -- Признаки читаемости
    flesch_reading_ease FLOAT NULL,
    flesch_kincaid_grade FLOAT NULL,
    automated_readability_index FLOAT NULL,
    coleman_liau_index FLOAT NULL,
    gunning_fog FLOAT NULL,
    smog_index FLOAT NULL,
    reading_time FLOAT NULL,
    
    -- Лингвистические признаки
    type_token_ratio FLOAT NULL,
    hapax_ratio FLOAT NULL,
    academic_density FLOAT NULL,
    modal_density FLOAT NULL,
    passive_density FLOAT NULL,
    
    -- Дополнительные Pangram признаки
    pangram_window_variance FLOAT NULL,
    pangram_ai_sentences_count INT NULL,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_filename (filename),
    INDEX idx_file_type (file_type),
    INDEX idx_ai_likelihood (ai_likelihood),
    INDEX idx_prediction (prediction),
    INDEX idx_created_at (created_at),
    INDEX idx_api_endpoint (api_endpoint)
);

-- Добавление новых полей к существующей таблице (миграция)
-- Выполнять только если таблица уже существует без новых полей

-- Статистические признаки
ALTER TABLE detection ADD COLUMN IF NOT EXISTS word_count INT NULL;
ALTER TABLE detection ADD COLUMN IF NOT EXISTS sentence_count INT NULL;
ALTER TABLE detection ADD COLUMN IF NOT EXISTS paragraph_count INT NULL;
ALTER TABLE detection ADD COLUMN IF NOT EXISTS avg_word_length FLOAT NULL;
ALTER TABLE detection ADD COLUMN IF NOT EXISTS avg_sentence_length FLOAT NULL;
ALTER TABLE detection ADD COLUMN IF NOT EXISTS sentence_length_variance FLOAT NULL;
ALTER TABLE detection ADD COLUMN IF NOT EXISTS punctuation_density FLOAT NULL;
ALTER TABLE detection ADD COLUMN IF NOT EXISTS uppercase_ratio FLOAT NULL;

-- Признаки читаемости
ALTER TABLE detection ADD COLUMN IF NOT EXISTS flesch_reading_ease FLOAT NULL;
ALTER TABLE detection ADD COLUMN IF NOT EXISTS flesch_kincaid_grade FLOAT NULL;
ALTER TABLE detection ADD COLUMN IF NOT EXISTS automated_readability_index FLOAT NULL;
ALTER TABLE detection ADD COLUMN IF NOT EXISTS coleman_liau_index FLOAT NULL;
ALTER TABLE detection ADD COLUMN IF NOT EXISTS gunning_fog FLOAT NULL;
ALTER TABLE detection ADD COLUMN IF NOT EXISTS smog_index FLOAT NULL;
ALTER TABLE detection ADD COLUMN IF NOT EXISTS reading_time FLOAT NULL;

-- Лингвистические признаки
ALTER TABLE detection ADD COLUMN IF NOT EXISTS type_token_ratio FLOAT NULL;
ALTER TABLE detection ADD COLUMN IF NOT EXISTS hapax_ratio FLOAT NULL;
ALTER TABLE detection ADD COLUMN IF NOT EXISTS academic_density FLOAT NULL;
ALTER TABLE detection ADD COLUMN IF NOT EXISTS modal_density FLOAT NULL;
ALTER TABLE detection ADD COLUMN IF NOT EXISTS passive_density FLOAT NULL;

-- Дополнительные Pangram признаки
ALTER TABLE detection ADD COLUMN IF NOT EXISTS pangram_window_variance FLOAT NULL;
ALTER TABLE detection ADD COLUMN IF NOT EXISTS pangram_ai_sentences_count INT NULL;

-- Индексы для новых полей (для аналитики)
CREATE INDEX IF NOT EXISTS idx_word_count ON detection(word_count);
CREATE INDEX IF NOT EXISTS idx_sentence_count ON detection(sentence_count);
CREATE INDEX IF NOT EXISTS idx_flesch_reading_ease ON detection(flesch_reading_ease);
CREATE INDEX IF NOT EXISTS idx_type_token_ratio ON detection(type_token_ratio);

-- Таблица пользователей (расширенная)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    role ENUM('student', 'teacher', 'admin') NOT NULL DEFAULT 'student',
    group_id INT NULL,
    student_id VARCHAR(50) NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME NULL,
    INDEX idx_email (email),
    INDEX idx_role (role),
    INDEX idx_group_id (group_id)
);

-- Таблица групп
CREATE TABLE IF NOT EXISTS groups (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    course_code VARCHAR(50) NOT NULL,
    academic_year VARCHAR(20) NOT NULL,
    semester INT NULL,
    faculty VARCHAR(255) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_course_code (course_code),
    INDEX idx_academic_year (academic_year)
);

-- Таблица фрагментов текста для плагиата
CREATE TABLE IF NOT EXISTS text_fragments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    detection_id INT NOT NULL,
    fragment_text LONGTEXT NOT NULL,
    start_position INT NOT NULL,
    end_position INT NOT NULL,
    word_count INT NOT NULL,
    fragment_hash VARCHAR(32) NOT NULL,
    embedding_vector JSON NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (detection_id) REFERENCES detection(id) ON DELETE CASCADE,
    INDEX idx_detection_id (detection_id),
    INDEX idx_fragment_hash (fragment_hash),
    INDEX idx_word_count (word_count)
);

-- Таблица совпадений плагиата
CREATE TABLE IF NOT EXISTS plagiarism_matches (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_detection_id INT NOT NULL,
    target_detection_id INT NOT NULL,
    source_fragment_id INT NOT NULL,
    target_fragment_id INT NOT NULL,
    similarity_score FLOAT NOT NULL,
    match_type ENUM('exact', 'near_exact', 'paraphrase', 'semantic') NOT NULL,
    match_length INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_detection_id) REFERENCES detection(id) ON DELETE CASCADE,
    FOREIGN KEY (target_detection_id) REFERENCES detection(id) ON DELETE CASCADE,
    FOREIGN KEY (source_fragment_id) REFERENCES text_fragments(id) ON DELETE CASCADE,
    FOREIGN KEY (target_fragment_id) REFERENCES text_fragments(id) ON DELETE CASCADE,
    INDEX idx_source_detection (source_detection_id),
    INDEX idx_target_detection (target_detection_id),
    INDEX idx_similarity_score (similarity_score),
    INDEX idx_match_type (match_type)
);

-- Таблица отчетов о плагиате
CREATE TABLE IF NOT EXISTS plagiarism_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    detection_id INT NOT NULL,
    total_similarity_score FLOAT NOT NULL DEFAULT 0.0,
    unique_matches_count INT NOT NULL DEFAULT 0,
    total_matched_words INT NOT NULL DEFAULT 0,
    report_data JSON NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (detection_id) REFERENCES detection(id) ON DELETE CASCADE,
    INDEX idx_detection_id (detection_id),
    INDEX idx_total_similarity_score (total_similarity_score)
);

-- Представление для аналитики с расширенными признаками
CREATE OR REPLACE VIEW detection_analytics AS
SELECT 
    d.id,
    d.filename,
    d.file_type,
    d.text_length,
    d.api_endpoint,
    d.ai_likelihood,
    d.prediction,
    d.created_at,
    
    -- Статистические признаки
    d.word_count,
    d.sentence_count,
    d.avg_word_length,
    d.punctuation_density,
    
    -- Признаки читаемости
    d.flesch_reading_ease,
    d.coleman_liau_index,
    
    -- Лингвистические признаки
    d.type_token_ratio,
    d.academic_density,
    
    -- Плагиат
    pr.total_similarity_score as plagiarism_score,
    pr.unique_matches_count as plagiarism_matches,
    
    -- Категории риска
    CASE 
        WHEN d.ai_likelihood >= 0.8 THEN 'HIGH_AI_RISK'
        WHEN d.ai_likelihood >= 0.5 THEN 'MEDIUM_AI_RISK'
        WHEN d.ai_likelihood >= 0.2 THEN 'LOW_AI_RISK'
        ELSE 'MINIMAL_AI_RISK'
    END as ai_risk_category,
    
    CASE 
        WHEN pr.total_similarity_score >= 0.7 THEN 'HIGH_PLAGIARISM'
        WHEN pr.total_similarity_score >= 0.3 THEN 'MEDIUM_PLAGIARISM'
        WHEN pr.total_similarity_score >= 0.1 THEN 'LOW_PLAGIARISM'
        ELSE 'ORIGINAL'
    END as plagiarism_category
    
FROM detection d
LEFT JOIN plagiarism_reports pr ON d.id = pr.detection_id;

-- Функция для обновления статистики
DELIMITER //
CREATE OR REPLACE FUNCTION get_feature_statistics()
RETURNS JSON
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE result JSON;
    
    SELECT JSON_OBJECT(
        'total_detections', COUNT(*),
        'avg_ai_likelihood', ROUND(AVG(ai_likelihood), 3),
        'avg_word_count', ROUND(AVG(word_count), 0),
        'avg_sentence_count', ROUND(AVG(sentence_count), 0),
        'avg_flesch_score', ROUND(AVG(flesch_reading_ease), 2),
        'avg_type_token_ratio', ROUND(AVG(type_token_ratio), 3),
        'high_ai_risk_count', SUM(CASE WHEN ai_likelihood >= 0.7 THEN 1 ELSE 0 END),
        'features_extracted_count', SUM(CASE WHEN word_count IS NOT NULL THEN 1 ELSE 0 END)
    ) INTO result
    FROM detection
    WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY);
    
    RETURN result;
END //
DELIMITER ;

-- Триггер для автоматического обновления статистики
DELIMITER //
CREATE OR REPLACE TRIGGER update_detection_stats
    AFTER INSERT ON detection
    FOR EACH ROW
BEGIN
    -- Можно добавить логику для автоматического обновления статистики
    -- Например, кеширование или обновление агрегированных данных
    SET @dummy = 1;
END //
DELIMITER ; 