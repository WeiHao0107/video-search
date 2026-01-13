-- SQL script to create the database schema for the Video Search project.

-- Enable UUID extension if not already enabled.
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table for source files (videos, pdfs, etc.)
CREATE TABLE IF NOT EXISTS source_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR NOT NULL,
    file_type VARCHAR NOT NULL,
    file_path VARCHAR,
    author VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata_info JSONB
);

-- Table for content chunks (subtitles, text from pages, etc.)
CREATE TABLE IF NOT EXISTS contents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_file_id UUID NOT NULL,
    type VARCHAR NOT NULL,
    content TEXT NOT NULL,
    custom JSONB,
    
    CONSTRAINT fk_source_file
        FOREIGN KEY (source_file_id)
        REFERENCES source_files(id)
        ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_source_files_file_type ON source_files(file_type);
CREATE INDEX IF NOT EXISTS idx_contents_source_file_id ON contents(source_file_id);
CREATE INDEX IF NOT EXISTS idx_contents_type ON contents(type);

COMMENT ON TABLE source_files IS 'Stores metadata about source files like videos, audios, or documents.';
COMMENT ON COLUMN source_files.file_path IS 'Absolute path to the file, used for serving it.';
COMMENT ON TABLE contents IS 'Stores chunks of content extracted from source files, e.g., subtitles or text blocks.';
COMMENT ON COLUMN contents.custom IS 'Flexible JSON field for storing context-specific data like timestamps or page numbers.';
