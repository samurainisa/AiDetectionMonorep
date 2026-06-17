#!/usr/bin/env python3
"""
Дообучение DeBERTa на JSON датасете для детекции ИИ-контента
"""
import os
import json
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModel
from torch.optim import AdamW  # Исправленный импорт
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

class AIDataset(Dataset):
    """Датасет для обучения детектора ИИ с расширенными признаками"""
    
    def __init__(self, data, tokenizer, max_length=256, use_features=True):
        self.data = data
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.use_features = use_features
        
        # Список признаков для использования
        self.feature_columns = [
            'word_count', 'sentence_count', 'avg_sentence_length',
            'punctuation_density', 'uppercase_ratio', 'russian_readability',
            'type_token_ratio', 'hapax_ratio', 'burstiness', 'mtld_diversity',
            'bigram_uniqueness', 'trigram_uniqueness', 'lexical_predictability'
        ]
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        text = str(item['extracted_text'])
        label = float(item['is_ai_generated'])
        
        # Токенизация текста
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )
        
        result = {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.float32)
        }
        
        # Добавляем статистические признаки если нужно
        if self.use_features:
            features = []
            for col in self.feature_columns:
                value = item.get(col, 0.0)
                features.append(float(value) if value is not None else 0.0)
            
            result['features'] = torch.tensor(features, dtype=torch.float32)
        
        return result

class HybridDetector(nn.Module):
    """Гибридная модель: DeBERTa + статистические признаки"""
    
    def __init__(self, model_name='microsoft/deberta-v3-base', num_features=13, use_features=True):
        super().__init__()
        
        self.use_features = use_features
        self.deberta = AutoModel.from_pretrained(model_name)
        self.dropout = nn.Dropout(0.1)
        
        hidden_size = self.deberta.config.hidden_size
        
        if use_features:
            # Обработка статистических признаков
            self.feature_processor = nn.Sequential(
                nn.Linear(num_features, 128),
                nn.ReLU(),
                nn.Dropout(0.1),
                nn.Linear(128, 64),
                nn.ReLU()
            )
            
            # Объединенный классификатор
            self.classifier = nn.Sequential(
                nn.Linear(hidden_size + 64, 256),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.Linear(256, 1),
                nn.Sigmoid()
            )
        else:
            # Только текстовый классификатор
            self.classifier = nn.Sequential(
                nn.Linear(hidden_size, 256),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.Linear(256, 1),
                nn.Sigmoid()
            )
    
    def forward(self, input_ids, attention_mask, features=None):
        # Получаем представление от DeBERTa
        outputs = self.deberta(input_ids=input_ids, attention_mask=attention_mask)
        text_repr = outputs.last_hidden_state[:, 0, :]  # [CLS] token
        text_repr = self.dropout(text_repr)
        
        if self.use_features and features is not None:
            # Обрабатываем статистические признаки
            feature_repr = self.feature_processor(features)
            
            # Объединяем представления
            combined = torch.cat([text_repr, feature_repr], dim=1)
            output = self.classifier(combined)
        else:
            output = self.classifier(text_repr)
        
        return output.squeeze()

class DeBERTaTrainer:
    """Класс для обучения модели"""
    
    def __init__(self, dataset_path='dataset.json', use_features=True):
        self.dataset_path = dataset_path
        self.use_features = use_features
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"🔧 Используется устройство: {self.device}")
        
        # Инициализация токенизатора
        self.tokenizer = AutoTokenizer.from_pretrained('microsoft/deberta-v3-base')
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
    
    def load_data(self):
        """Загрузка данных из JSON файла"""
        print(f"📊 Загрузка данных из {self.dataset_path}...")
        
        if not os.path.exists(self.dataset_path):
            print(f"❌ Файл датасета не найден: {self.dataset_path}")
            return None
        
        with open(self.dataset_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"📈 Загружено {len(data)} записей")
        
        # Фильтрация данных
        filtered_data = []
        for item in data:
            if (item.get('extracted_text') and 
                len(item['extracted_text']) > 50 and
                'is_ai_generated' in item):
                filtered_data.append(item)
        
        print(f"✅ После фильтрации: {len(filtered_data)} записей")
        
        if len(filtered_data) < 10:
            print("❌ Недостаточно данных для обучения")
            return None
        
        # Статистика классов
        labels = [item['is_ai_generated'] for item in filtered_data]
        unique, counts = np.unique(labels, return_counts=True)
        print(f"📊 Распределение классов:")
        for label, count in zip(unique, counts):
            class_name = "ИИ" if label == 1 else "Человек"
            print(f"   {class_name}: {count}")
        
        return filtered_data
    
    def prepare_data_loaders(self, data, test_size=0.2, batch_size=4):
        """Подготовка загрузчиков данных"""
        print("🔄 Подготовка данных для обучения...")
        
        # Разделение данных
        labels = [item['is_ai_generated'] for item in data]
        train_data, test_data = train_test_split(
            data, test_size=test_size, random_state=42, stratify=labels
        )
        
        print(f"📊 Размеры выборок:")
        print(f"   Train: {len(train_data)}")
        print(f"   Test: {len(test_data)}")
        
        # Создание датасетов
        train_dataset = AIDataset(train_data, self.tokenizer, use_features=self.use_features)
        test_dataset = AIDataset(test_data, self.tokenizer, use_features=self.use_features)
        
        # Создание загрузчиков
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
        
        return train_loader, test_loader
    
    def train_model(self, train_loader, test_loader, epochs=3, learning_rate=2e-5):
        """Обучение модели"""
        print("🤖 Инициализация модели...")
        
        model = HybridDetector(use_features=self.use_features)
        model.to(self.device)
        
        # Подсчет параметров
        total_params = sum(p.numel() for p in model.parameters())
        print(f"📊 Параметров модели: {total_params:,}")
        
        # Оптимизатор и функция потерь
        optimizer = AdamW(model.parameters(), lr=learning_rate, weight_decay=0.01)
        criterion = nn.BCELoss()
        
        print("🚀 Начало обучения...")
        
        # История обучения
        history = {'train_loss': [], 'train_acc': [], 'test_acc': []}
        
        for epoch in range(epochs):
            # Обучение
            model.train()
            total_loss = 0
            correct = 0
            total = 0
            
            print(f"\n📅 Эпоха {epoch + 1}/{epochs}")
            
            for batch_idx, batch in enumerate(train_loader):
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['labels'].to(self.device)
                
                features = None
                if self.use_features:
                    features = batch['features'].to(self.device)
                
                optimizer.zero_grad()
                outputs = model(input_ids, attention_mask, features)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
                predictions = (outputs > 0.5).float()
                correct += (predictions == labels).sum().item()
                total += labels.size(0)
                
                if batch_idx % 5 == 0:
                    print(f"   Batch {batch_idx}: Loss={loss.item():.4f}")
            
            train_loss = total_loss / len(train_loader)
            train_acc = correct / total
            
            # Тестирование
            test_acc = self.evaluate_model(model, test_loader)
            
            # Сохранение истории
            history['train_loss'].append(train_loss)
            history['train_acc'].append(train_acc)
            history['test_acc'].append(test_acc)
            
            print(f"   Train Loss: {train_loss:.4f}")
            print(f"   Train Acc: {train_acc:.4f}")
            print(f"   Test Acc: {test_acc:.4f}")
        
        # Сохранение модели
        os.makedirs('models', exist_ok=True)
        model_path = f'models/deberta_detector_{"hybrid" if self.use_features else "text"}.pth'
        torch.save(model.state_dict(), model_path)
        print(f"💾 Модель сохранена: {model_path}")
        
        return model, history
    
    def evaluate_model(self, model, test_loader):
        """Оценка модели"""
        model.eval()
        correct = 0
        total = 0
        
        with torch.no_grad():
            for batch in test_loader:
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['labels'].to(self.device)
                
                features = None
                if self.use_features:
                    features = batch['features'].to(self.device)
                
                outputs = model(input_ids, attention_mask, features)
                predictions = (outputs > 0.5).float()
                correct += (predictions == labels).sum().item()
                total += labels.size(0)
        
        return correct / total
    
    def detailed_evaluation(self, model, test_loader):
        """Детальная оценка модели"""
        print("🧪 Детальное тестирование...")
        
        model.eval()
        all_predictions = []
        all_labels = []
        all_probabilities = []
        
        with torch.no_grad():
            for batch in test_loader:
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['labels'].to(self.device)
                
                features = None
                if self.use_features:
                    features = batch['features'].to(self.device)
                
                outputs = model(input_ids, attention_mask, features)
                predictions = (outputs > 0.5).float()
                
                all_predictions.extend(predictions.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())
                all_probabilities.extend(outputs.cpu().numpy())
        
        # Метрики
        accuracy = accuracy_score(all_labels, all_predictions)
        print(f"📊 Результаты тестирования:")
        print(f"   Accuracy: {accuracy:.4f}")
        print("\n📋 Детальный отчет:")
        print(classification_report(all_labels, all_predictions, 
                                  target_names=['Человек', 'ИИ']))
        
        # Матрица ошибок
        cm = confusion_matrix(all_labels, all_predictions)
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                   xticklabels=['Человек', 'ИИ'], yticklabels=['Человек', 'ИИ'])
        plt.title('Confusion Matrix')
        plt.xlabel('Predicted')
        plt.ylabel('Actual')
        plt.tight_layout()
        plt.savefig('confusion_matrix.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        return accuracy
    
    def test_examples(self, model):
        """Тестирование на примерах"""
        print("\n🔍 Тестирование на примерах:")
        
        test_cases = [
            {
                'text': "Искусственный интеллект представляет собой революционную технологию, которая трансформирует современное общество. Данная область демонстрирует значительный потенциал для оптимизации различных процессов и повышения эффективности систем.",
                'expected': 'ИИ'
            },
            {
                'text': "Вчера ходил к врачу. Очередь была огромная! Сидел два часа, думал уже домой уйти. Но врач оказался очень хороший, все подробно объяснил. Теперь понимаю, что с моим здоровьем делать дальше.",
                'expected': 'Человек'
            }
        ]
        
        model.eval()
        
        for i, test_case in enumerate(test_cases, 1):
            text = test_case['text']
            expected = test_case['expected']
            
            # Токенизация
            encoding = self.tokenizer(
                text,
                truncation=True,
                padding='max_length',
                max_length=256,
                return_tensors='pt'
            )
            
            input_ids = encoding['input_ids'].to(self.device)
            attention_mask = encoding['attention_mask'].to(self.device)
            
            # Создаем фиктивные признаки если нужно
            features = None
            if self.use_features:
                # Базовые признаки для примера
                dummy_features = [
                    len(text.split()),  # word_count
                    len([s for s in text.split('.') if s.strip()]),  # sentence_count
                    len(text.split()) / max(1, len([s for s in text.split('.') if s.strip()])),  # avg_sentence_length
                    sum(1 for c in text if c in '.,!?;:') / len(text),  # punctuation_density
                    sum(1 for c in text if c.isupper()) / len(text),  # uppercase_ratio
                    50.0,  # russian_readability (dummy)
                    0.7,   # type_token_ratio (dummy)
                    0.3,   # hapax_ratio (dummy)
                    0.5,   # burstiness (dummy)
                    1.0,   # mtld_diversity (dummy)
                    0.9,   # bigram_uniqueness (dummy)
                    0.95,  # trigram_uniqueness (dummy)
                    0.3    # lexical_predictability (dummy)
                ]
                features = torch.tensor(dummy_features, dtype=torch.float32).unsqueeze(0).to(self.device)
            
            # Предсказание
            with torch.no_grad():
                output = model(input_ids, attention_mask, features)
                probability = output.item()
                prediction = "ИИ" if probability > 0.5 else "Человек"
            
            print(f"\n📝 Тест {i}:")
            print(f"   Текст: {text[:80]}...")
            print(f"   Ожидалось: {expected}")
            print(f"   Предсказано: {prediction}")
            print(f"   Вероятность ИИ: {probability:.4f}")
            print(f"   Результат: {'✅' if prediction == expected else '❌'}")

def main():
    """Основная функция"""
    print("🎯 Запуск дообучения DeBERTa на JSON датасете")
    
    # Выбор режима
    use_features = input("Использовать статистические признаки? (y/n): ").lower() == 'y'
    dataset_path = input("Путь к JSON файлу (по умолчанию dataset.json): ").strip()
    if not dataset_path:
        dataset_path = 'dataset.json'
    
    # Инициализация тренера
    trainer = DeBERTaTrainer(dataset_path=dataset_path, use_features=use_features)
    
    # Загрузка данных
    data = trainer.load_data()
    if data is None:
        return
    
    # Подготовка данных
    train_loader, test_loader = trainer.prepare_data_loaders(data)
    
    # Обучение
    model, history = trainer.train_model(train_loader, test_loader)
    
    # Детальная оценка
    trainer.detailed_evaluation(model, test_loader)
    
    # Тестирование на примерах
    trainer.test_examples(model)
    
    print("✅ Обучение завершено!")

if __name__ == "__main__":
    main() 