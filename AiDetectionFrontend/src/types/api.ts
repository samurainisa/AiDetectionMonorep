// Common API errors
export interface APIError {
  error: string
}

// Request payloads
export interface AnalyzeTextRequest {
  text: string
}

export interface AnalyzeBatchRequest {
  texts: string[]
}

// Pangram V3 windows normalized for frontend rendering
export interface WindowData {
  text: string
  ai_likelihood: number
  start_index: number
  end_index: number
  prediction?: string
  label?: string
  ai_assistance_score?: number
  confidence?: string
  word_count?: number
  token_length?: number
  llm_prediction?: Record<string, number>
  metadata?: Record<string, unknown>
}

// Unified Pangram response (legacy + V3)
export interface PangramResponse {
  text?: string
  version?: string
  headline?: string
  prediction?: string
  prediction_short?: 'AI' | 'AI-Assisted' | 'Human' | 'Mixed' | string

  ai_likelihood?: number
  max_ai_likelihood?: number
  avg_ai_likelihood?: number
  fraction_ai_content?: number

  fraction_ai?: number
  fraction_ai_assisted?: number
  fraction_human?: number
  num_ai_segments?: number
  num_ai_assisted_segments?: number
  num_human_segments?: number
  dashboard_link?: string

  windows?: WindowData[]
  llm_prediction?: Record<string, number>
  llm_prediction_ai_likelihood?: number
  llm_prediction_label?: string
  llm_prediction_request_id?: string
  llm_prediction_source?: string
}

// Main analysis responses
export interface AnalyzeResponse {
  detection_id: number
  filename?: string
  file_type?: string
  text_length: number
  api_endpoint_used: string
  pangram_response: PangramResponse
  plagiarism_report?: PlagiarismReport
  plagiarism_pending?: boolean
  plagiarism_status?: PlagiarismStatus
}

export interface BatchAnalyzeResult {
  id?: number
  ai_likelihood?: number
  prediction?: string
  error?: string
}

export interface AnalyzeBatchResponse {
  results: BatchAnalyzeResult[]
}

// Plagiarism types
export interface PlagiarismMatch {
  source_detection_id: number
  source_fragment_pos: number
  target_fragment_pos: number
  similarity_score: number
  matched_text: string
  match_type: string
}

export interface SimilarDocument {
  detection_id: number
  filename: string
  similarity_percentage: number
  matched_fragments: number
  created_at: string
}

export interface PlagiarismReport {
  detection_id: number
  total_similarity_score: number
  plagiarism_level: 'original' | 'low' | 'moderate' | 'high' | 'very_high'
  originality_percentage: number
  total_fragments: number
  matched_fragments: number
  matches: PlagiarismMatch[]
  similar_documents: SimilarDocument[]
}

export type PlagiarismStatus = 'ready' | 'pending' | 'unknown' | 'unavailable'

// History and detail responses
export interface Detection {
  id: number
  filename: string
  file_type: string
  text_length: number
  api_endpoint: string
  ai_likelihood?: number
  fraction_ai_content?: number
  fraction_human?: number
  prediction_short?: string
  headline?: string
  prediction?: string
  full_response?: PangramResponse
  created_at: string
  plagiarism_originality?: number
  plagiarism_level?: string
  plagiarism_pending?: boolean
  plagiarism_status?: PlagiarismStatus
}

export interface HistoryResponse {
  total: number
  pages: number
  current_page: number
  per_page?: number
  detections: Detection[]
}

export interface DetectionDetail {
  id: number
  filename: string
  file_type: string
  text_length: number
  extracted_text: string
  api_endpoint: string
  ai_likelihood?: number
  max_ai_likelihood?: number
  avg_ai_likelihood?: number
  prediction?: string
  fraction_ai_content?: number
  full_response: PangramResponse
  created_at: string
  plagiarism_report?: PlagiarismReport
  plagiarism_pending?: boolean
  plagiarism_status?: PlagiarismStatus
  text_features?: {
    basic?: {
      word_count: number
      sentence_count: number
      avg_sentence_length: number
      punctuation_density: number
      uppercase_ratio: number
    }
    linguistic?: {
      type_token_ratio: number
      hapax_ratio: number
    }
    ai_detection?: {
      burstiness: number
      lexical_predictability: number
      bigram_uniqueness: number
      trigram_uniqueness: number
      pronoun_bias_first_person: number
      mtld_diversity: number
    }
    readability?: {
      russian_readability: number
    }
    pangram_extended?: {
      pangram_ai_sentences_count: number
      pangram_window_burstiness?: number
      pangram_window_variance?: number
    }
  }
}

// Stats
export interface StatsResponse {
  total_analyses: number
  ai_generated: number
  human_generated: number
  avg_ai_likelihood: number
  recent_analyses: number
  ai_percentage: number
}

// Upload helpers
export interface FileUploadData {
  file: File
}

export const ALLOWED_FILE_TYPES = ['pdf', 'docx', 'doc', 'txt'] as const
export type AllowedFileType = (typeof ALLOWED_FILE_TYPES)[number]

export interface TextSegment {
  text: string
  likelihood: number
  start_index: number
  end_index: number
  prediction?: string
  index: number
}

// Filters
export interface HistoryFilters {
  dateFrom?: string
  dateTo?: string
  fileType?: string
  prediction?: string
  aiLikelihoodMin?: number
  aiLikelihoodMax?: number
  search?: string
}

export interface FilterOption {
  label: string
  value: string | number
}

