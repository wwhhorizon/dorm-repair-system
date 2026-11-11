-- MySQL 8.4 schema; UTF-8; generated from SQLAlchemy models.

CREATE DATABASE IF NOT EXISTS repair CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE repair;


CREATE TABLE buildings (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(60) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)

;


CREATE TABLE users (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	username VARCHAR(40) NOT NULL, 
	password_hash VARCHAR(128) NOT NULL, 
	`role` VARCHAR(16) NOT NULL, 
	email VARCHAR(120), 
	active INTEGER NOT NULL, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	CHECK (role in ('student','admin','technician')), 
	UNIQUE (username)
)

;


CREATE TABLE audit_logs (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	actor_id INTEGER, 
	action VARCHAR(60) NOT NULL, 
	detail TEXT, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(actor_id) REFERENCES users (id)
)

;


CREATE TABLE login_sessions (
	token_hash VARCHAR(64) NOT NULL, 
	user_id INTEGER NOT NULL, 
	expires DATETIME NOT NULL, 
	PRIMARY KEY (token_hash), 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;


CREATE TABLE rooms (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	building_id INTEGER NOT NULL, 
	name VARCHAR(30) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(building_id) REFERENCES buildings (id)
)

;


CREATE TABLE tickets (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	student_id INTEGER NOT NULL, 
	room_id INTEGER NOT NULL, 
	description TEXT NOT NULL, 
	category VARCHAR(20) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	assignee_id INTEGER, 
	scheduled_at DATETIME, 
	version INTEGER NOT NULL, 
	created_at DATETIME, 
	updated_at DATETIME, 
	completed_at DATETIME, 
	PRIMARY KEY (id), 
	CHECK (category in ('water','electric','door','furniture','other')), 
	CHECK (status in ('pending','assigned','working','review','completed','cancelled')), 
	FOREIGN KEY(student_id) REFERENCES users (id), 
	FOREIGN KEY(room_id) REFERENCES rooms (id), 
	FOREIGN KEY(assignee_id) REFERENCES users (id)
)

;

CREATE INDEX ix_tickets_status ON tickets (status);

CREATE INDEX ix_tickets_student_id ON tickets (student_id);

CREATE INDEX ix_tickets_created_at ON tickets (created_at);


CREATE TABLE attachments (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	ticket_id INTEGER NOT NULL, 
	actor_id INTEGER NOT NULL, 
	path VARCHAR(100) NOT NULL, 
	mime VARCHAR(40) NOT NULL, 
	purpose VARCHAR(20) NOT NULL, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ticket_id) REFERENCES tickets (id), 
	FOREIGN KEY(actor_id) REFERENCES users (id)
)

;


CREATE TABLE evaluations (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	ticket_id INTEGER NOT NULL, 
	score INTEGER NOT NULL, 
	comment TEXT, 
	PRIMARY KEY (id), 
	CHECK (score >= 1 and score <= 5), 
	UNIQUE (ticket_id), 
	FOREIGN KEY(ticket_id) REFERENCES tickets (id)
)

;


CREATE TABLE predictions (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	ticket_id INTEGER NOT NULL, 
	category VARCHAR(20) NOT NULL, 
	confidence FLOAT NOT NULL, 
	model_version VARCHAR(80) NOT NULL, 
	source VARCHAR(10) NOT NULL, 
	accepted INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (confidence >= 0 and confidence <= 1), 
	CHECK (category in ('water','electric','door','furniture','other')), 
	UNIQUE (ticket_id), 
	FOREIGN KEY(ticket_id) REFERENCES tickets (id)
)

;


CREATE TABLE ticket_events (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	ticket_id INTEGER NOT NULL, 
	actor_id INTEGER NOT NULL, 
	action VARCHAR(30) NOT NULL, 
	from_state VARCHAR(20) NOT NULL, 
	to_state VARCHAR(20) NOT NULL, 
	note TEXT, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ticket_id) REFERENCES tickets (id), 
	FOREIGN KEY(actor_id) REFERENCES users (id)
)

;

CREATE INDEX ix_ticket_events_ticket_id ON ticket_events (ticket_id);