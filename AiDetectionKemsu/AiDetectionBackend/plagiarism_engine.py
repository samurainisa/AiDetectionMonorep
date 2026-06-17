#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Система антиплагиата - основной движок
"""

import hashlib
import json
import re
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import difflib

class PlagiarismLevel(Enum):
    ORIGINAL = "original"        # 0-15%
    LOW = "low"                 # 15-30%
    MODERATE = "moderate"       # 30-50%
    HIGH = "high"               # 50-70%
    VERY_HIGH = "very_high"     # 70%+

@dataclass
class TextFragment:
    text: str
    start_pos: int
    end_pos: int
    detection_id: int
    fragment_hash: str = ""
    shingles: Set[str] = None
    simhash: int = 0
    
    def __post_init__(self):
        if not self.fragment_hash:
            self.fragment_hash = hashlib.md5(self.text.encode()).hexdigest()
        if self.shingles is None:
            self.shingles = self._generate_shingles()
        if self.simhash == 0:
            self.simhash = self._generate_simhash()
    
    def _generate_shingles(self, k=3) -> Set[str]:
        """Генерирует k-граммы (шинглы) из текста"""
        words = re.findall(r'\b\w+\b', self.text.lower())
        if len(words) < k:
            return {' '.join(words)}
        return {' '.join(words[i:i+k]) for i in range(len(words) - k + 1)}
    
    def _generate_simhash(self) -> int:
        """Генерирует SimHash для быстрого сравнения"""
        features = list(self.shingles)
        if not features:
            return 0
        
        v = [0] * 64
        for feature in features:
            h = int(hashlib.md5(feature.encode()).hexdigest(), 16)
            for i in range(64):
                if h & (1 << i):
                    v[i] += 1
                else:
                    v[i] -= 1
        
        result = 0
        for i in range(64):
            if v[i] > 0:
                result |= (1 << i)
        return result

@dataclass
class PlagiarismMatch:
    source_detection_id: int
    source_fragment_pos: int
    target_fragment_pos: int
    similarity_score: float
    matched_text: str
    match_type: str = "text_similarity"
    
@dataclass
class SimilarDocument:
    detection_id: int
    filename: str
    similarity_percentage: float
    matched_fragments: int
    created_at: str

@dataclass
class PlagiarismReport:
    detection_id: int
    total_similarity_score: float
    plagiarism_level: PlagiarismLevel
    matches: List[PlagiarismMatch]
    similar_documents: List[SimilarDocument]
    originality_percentage: float
    total_fragments: int
    matched_fragments: int
    
    def to_dict(self) -> Dict:
        return {
            'detection_id': self.detection_id,
            'total_similarity_score': self.total_similarity_score,
            'plagiarism_level': self.plagiarism_level.value,
            'originality_percentage': self.originality_percentage,
            'total_fragments': self.total_fragments,
            'matched_fragments': self.matched_fragments,
            'matches': [asdict(match) for match in self.matches],
            'similar_documents': [asdict(doc) for doc in self.similar_documents]
        }

class PlagiarismEngine:
    def __init__(self):
        # Параметры
        self.similarity_threshold = 0.15
        self.simhash_threshold = 10
        self.fragment_size = 30
        self.fragment_overlap = 0.5
        # Убираем зависимость от локальной БД: всё храним в PostgreSQL через SQLAlchemy-модели
        # Локальный кэш отчётов (опционален) для совместимости с get_report()
        self._reports: Dict[int, Dict] = {}
    
    def _init_database(self):
        return
    
    def add_document_to_corpus(self, detection_id: int, filename: str, text: str) -> bool:
        """Добавляет документ в корпус для проверки плагиата"""
        try:
            fragments = self._create_text_fragments(text, detection_id)

            from core.database import db, PlagiarismCorpusDoc, PlagiarismFragment
            # Сохраняем метаданные документа
            doc = PlagiarismCorpusDoc(
                detection_id=detection_id,
                filename=filename,
                text_length=len(text.split()),
                is_active=True
            )
            # Удаляем старые фрагменты
            PlagiarismFragment.query.filter_by(detection_id=detection_id).delete()
            db.session.merge(doc)
            db.session.flush()
            # Сохраняем фрагменты
            for frag in fragments:
                db.session.add(PlagiarismFragment(
                    detection_id=detection_id,
                    fragment_text=frag.text,
                    start_pos=frag.start_pos,
                    end_pos=frag.end_pos,
                    fragment_hash=hashlib.md5(frag.text.encode()).hexdigest(),
                    shingles_json=json.dumps(list(frag.shingles), ensure_ascii=False),
                    simhash=str(frag.simhash)
                ))
            db.session.commit()

            return True
            
        except Exception as e:
            try:
                from core.database import db
                db.session.rollback()
            except Exception:
                pass
            print(f"Ошибка добавления в корпус: {e}")
            return False
    
    def check_plagiarism(self, detection_id: int, text: str, filename: str = "unknown") -> PlagiarismReport:
        """Проверяет текст на плагиат"""
        fragments = self._create_text_fragments(text, detection_id)
        matches = []
        similar_docs = {}
        
        if not fragments:
            return PlagiarismReport(
                detection_id=detection_id,
                total_similarity_score=0.0,
                plagiarism_level=PlagiarismLevel.ORIGINAL,
                matches=[],
                similar_documents=[],
                originality_percentage=100.0,
                total_fragments=0,
                matched_fragments=0
            )
        
        # Проверяем каждый фрагмент против корпуса (кроме самого себя)
        for fragment in fragments:
            fragment_matches = self._find_fragment_matches(fragment, detection_id)
            matches.extend(fragment_matches)
            
            # Группируем по документам
            for match in fragment_matches:
                doc_id = match.source_detection_id
                if doc_id not in similar_docs:
                    similar_docs[doc_id] = {
                        'matches': 0,
                        'total_similarity': 0.0
                    }
                similar_docs[doc_id]['matches'] += 1
                similar_docs[doc_id]['total_similarity'] += match.similarity_score
        
        # Создаем список похожих документов
        similar_documents = []
        for doc_id, data in similar_docs.items():
            doc_info = self._get_document_info(doc_id)
            if doc_info:
                similarity_percentage = (data['total_similarity'] / data['matches']) * 100
                similar_documents.append(SimilarDocument(
                    detection_id=doc_id,
                    filename=doc_info['filename'],
                    similarity_percentage=similarity_percentage,
                    matched_fragments=data['matches'],
                    created_at=doc_info['created_at']
                ))
        
        # Сортируем по убыванию схожести
        similar_documents.sort(key=lambda x: x.similarity_percentage, reverse=True)
        
        # Вычисляем общие метрики
        # Совмещаем по целевым позициям, считаем среднюю схожесть по уникальным совпадениям
        unique_positions = {}
        for m in matches:
            key = (m.target_fragment_pos)
            unique_positions.setdefault(key, []).append(m.similarity_score)
        total_similarity = 0.0
        if unique_positions:
            totals = [max(scores) for scores in unique_positions.values()]
            total_similarity = sum(totals) / len(totals)
        matched_fragments_count = len(unique_positions)
        originality_percentage = max(0, 100 - (total_similarity * 100))
        
        # Определяем уровень плагиата
        plagiarism_level = self._get_plagiarism_level(originality_percentage)
        
        # Сохраняем отчет
        report = PlagiarismReport(
            detection_id=detection_id,
            total_similarity_score=total_similarity,
            plagiarism_level=plagiarism_level,
            matches=matches,
            similar_documents=similar_documents,
            originality_percentage=originality_percentage,
            total_fragments=len(fragments),
            matched_fragments=matched_fragments_count
        )
        
        self._save_report(report)
        return report
    
    def get_report(self, detection_id: int) -> Optional[PlagiarismReport]:
        """Получает сохраненный отчет"""
        data = self._reports.get(detection_id)
        if not data:
            return None
        return PlagiarismReport(
            detection_id=detection_id,
            total_similarity_score=data['total_similarity_score'],
            plagiarism_level=PlagiarismLevel(data['plagiarism_level']),
            originality_percentage=data['originality_percentage'],
            total_fragments=data['total_fragments'],
            matched_fragments=data['matched_fragments'],
            matches=[PlagiarismMatch(**m) for m in data['report_data'].get('matches', [])],
            similar_documents=[SimilarDocument(**d) for d in data['report_data'].get('similar_documents', [])]
        )
    
    def _create_text_fragments(self, text: str, detection_id: int) -> List[TextFragment]:
        """Разбивает текст на фрагменты"""
        words = text.split()
        if len(words) < self.fragment_size:
            return [TextFragment(
                text=text,
                start_pos=0,
                end_pos=len(text),
                detection_id=detection_id
            )]
        
        fragments = []
        step = int(self.fragment_size * (1 - self.fragment_overlap))
        
        for i in range(0, len(words) - self.fragment_size + 1, step):
            fragment_words = words[i:i + self.fragment_size]
            fragment_text = ' '.join(fragment_words)
            
            fragments.append(TextFragment(
                text=fragment_text,
                start_pos=i,
                end_pos=i + self.fragment_size,
                detection_id=detection_id
            ))
        
        return fragments
    
    def _find_fragment_matches(self, fragment: TextFragment, exclude_detection_id: int) -> List[PlagiarismMatch]:
        """Находит совпадения для фрагмента"""
        matches = []
        from core.database import PlagiarismFragment
        corpus_frag_q = PlagiarismFragment.query.filter(PlagiarismFragment.detection_id != exclude_detection_id).all()
        corpus_fragments = [
            (
                f.detection_id,
                f.fragment_text,
                f.start_pos,
                f.shingles_json,
                f.simhash
            ) for f in corpus_frag_q
        ]
        
        for corpus_frag in corpus_fragments:
            corpus_detection_id, corpus_text, corpus_start_pos, corpus_shingles_json, corpus_simhash = corpus_frag
            
            # SimHash фильтрация
            corpus_simhash_int = int(corpus_simhash)
            hamming_distance = bin(fragment.simhash ^ corpus_simhash_int).count('1')
            
            if hamming_distance <= self.simhash_threshold:
                # Точное сравнение через shingles
                corpus_shingles = set(json.loads(corpus_shingles_json))
                similarity = self._jaccard_similarity(fragment.shingles, corpus_shingles)
                
                if similarity >= self.similarity_threshold:
                    # Находим самый длинный общий фрагмент
                    lcs_ratio = self._longest_common_subsequence_ratio(fragment.text, corpus_text)
                    
                    if lcs_ratio > 0.2:  # Минимум 20% общего текста
                        final_similarity = max(similarity, lcs_ratio)
                        matches.append(PlagiarismMatch(
                            source_detection_id=corpus_detection_id,
                            source_fragment_pos=corpus_start_pos,
                            target_fragment_pos=fragment.start_pos,
                            similarity_score=final_similarity,
                            matched_text=fragment.text[:100] + "...",
                            match_type="text_similarity"
                        ))
        
        return matches
    
    def _jaccard_similarity(self, set1: Set[str], set2: Set[str]) -> float:
        """Вычисляет коэффициент Жаккара"""
        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union if union > 0 else 0.0
    
    def _longest_common_subsequence_ratio(self, text1: str, text2: str) -> float:
        """Вычисляет отношение длины LCS к длине текста"""
        seq_matcher = difflib.SequenceMatcher(None, text1.split(), text2.split())
        matching_blocks = seq_matcher.get_matching_blocks()
        
        total_matching_words = sum(block.size for block in matching_blocks)
        max_length = max(len(text1.split()), len(text2.split()))
        
        return total_matching_words / max_length if max_length > 0 else 0.0
    
    def _get_plagiarism_level(self, originality_percentage: float) -> PlagiarismLevel:
        """Определяет уровень плагиата"""
        if originality_percentage >= 85:
            return PlagiarismLevel.ORIGINAL
        elif originality_percentage >= 70:
            return PlagiarismLevel.LOW
        elif originality_percentage >= 50:
            return PlagiarismLevel.MODERATE
        elif originality_percentage >= 30:
            return PlagiarismLevel.HIGH
        else:
            return PlagiarismLevel.VERY_HIGH
    
    def _get_document_info(self, detection_id: int) -> Optional[Dict]:
        """Получает информацию о документе из БД (SQLAlchemy)"""
        try:
            from core.database import PlagiarismCorpusDoc
            doc = PlagiarismCorpusDoc.query.filter_by(detection_id=detection_id).first()
            if not doc:
                return None
            return {
                'filename': doc.filename,
                'created_at': doc.created_at.isoformat() if getattr(doc, 'created_at', None) else None
            }
        except Exception:
            return None
    
    def _save_report(self, report: PlagiarismReport):
        """Сохраняет отчет в базе данных"""
        report_data = {
            'matches': [asdict(match) for match in report.matches],
            'similar_documents': [asdict(doc) for doc in report.similar_documents]
        }
        self._reports[report.detection_id] = {
            'total_similarity_score': report.total_similarity_score,
            'plagiarism_level': report.plagiarism_level.value,
            'originality_percentage': report.originality_percentage,
            'total_fragments': report.total_fragments,
            'matched_fragments': report.matched_fragments,
            'report_data': report_data,
            'created_at': datetime.utcnow().isoformat()
        }
    
    def get_corpus_stats(self) -> Dict:
        """Получает статистику корпуса"""
        from core.database import PlagiarismCorpusDoc, PlagiarismFragment, db
        total_docs = PlagiarismCorpusDoc.query.filter_by(is_active=True).count()
        total_fragments = PlagiarismFragment.query.count()
        total_words = db.session.query(db.func.sum(PlagiarismCorpusDoc.text_length)).filter_by(is_active=True).scalar() or 0
        return {
            'total_documents': total_docs,
            'total_fragments': total_fragments,
            'total_words': total_words
        }

# Глобальный экземпляр движка
plagiarism_engine = PlagiarismEngine() 