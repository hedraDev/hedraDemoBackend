"""
Veritabanı Yönetim Modülü
MongoDB işlemleri ve yedekleme
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from pymongo import MongoClient, errors
from pymongo.collection import Collection


class DatabaseManager:
    """MongoDB veritabanı yönetimi için sınıf"""

    def __init__(self, uri: str, db_name: str, collection_name: str, backup_dir: str = "./backup"):
        """
        Args:
            uri: MongoDB bağlantı URI'si
            db_name: Veritabanı adı
            collection_name: Koleksiyon adı
            backup_dir: Yedekleme dizini
        """
        self.uri = uri
        self.db_name = db_name
        self.collection_name = collection_name
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.client: Optional[MongoClient] = None
        self.db = None
        self.collection: Optional[Collection] = None
        self.connected = False

    def connect(self) -> bool:
        """MongoDB'ye bağlan"""
        try:
            self.client = MongoClient(
                self.uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000
            )
            # Bağlantıyı test et
            self.client.server_info()

            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            self.connected = True

            return True

        except errors.ServerSelectionTimeoutError:
            print("MongoDB sunucusuna bağlanılamadı - timeout")
            self.connected = False
            return False

        except Exception as e:
            print(f"MongoDB bağlantı hatası: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """MongoDB bağlantısını kapat"""
        if self.client:
            self.client.close()
            self.connected = False

    def insert_test_result(self, test_data: Dict) -> Optional[str]:
        """Test sonucunu ekle"""
        if not self.connected:
            # Bağlantı yoksa yedek dosyaya yaz
            return self._backup_to_file(test_data)

        try:
            result = self.collection.insert_one(test_data)
            return str(result.inserted_id)

        except Exception as e:
            print(f"MongoDB insert hatası: {e}")
            # Hata durumunda yedek dosyaya yaz
            return self._backup_to_file(test_data)

    def _backup_to_file(self, test_data: Dict) -> Optional[str]:
        """Test verisini dosyaya yedekle"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            device_uuid = test_data.get('device_uuid', 'unknown')
            backup_file = self.backup_dir / f"test_{device_uuid}_{timestamp}.json"

            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(test_data, f, indent=2, ensure_ascii=False)

            print(f"Test verisi yedek dosyaya kaydedildi: {backup_file}")
            return str(backup_file)

        except Exception as e:
            print(f"Yedek dosya hatası: {e}")
            return None

    def get_test_by_uuid(self, device_uuid: str) -> Optional[Dict]:
        """UUID'ye göre test sonucunu getir"""
        if not self.connected:
            return None

        try:
            return self.collection.find_one({"device_uuid": device_uuid})
        except Exception as e:
            print(f"MongoDB sorgu hatası: {e}")
            return None

    def get_tests_by_date(self, start_date: datetime, end_date: datetime = None) -> List[Dict]:
        """Tarih aralığına göre testleri getir"""
        if not self.connected:
            return []

        if end_date is None:
            end_date = datetime.now()

        try:
            query = {
                "start_time": {
                    "$gte": start_date.isoformat(),
                    "$lte": end_date.isoformat()
                }
            }
            return list(self.collection.find(query).sort("start_time", -1))

        except Exception as e:
            print(f"MongoDB sorgu hatası: {e}")
            return []

    def get_statistics(self, days: int = 30) -> Dict:
        """İstatistikleri getir"""
        if not self.connected:
            return self._get_statistics_from_backup()

        try:
            start_date = datetime.now() - timedelta(days=days)

            pipeline = [
                {
                    "$match": {
                        "start_time": {"$gte": start_date.isoformat()}
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total_tests": {"$sum": 1},
                        "successful_tests": {
                            "$sum": {
                                "$cond": [{"$eq": ["$status", "completed"]}, 1, 0]
                            }
                        },
                        "failed_tests": {
                            "$sum": {
                                "$cond": [{"$ne": ["$status", "completed"]}, 1, 0]
                            }
                        },
                        "avg_duration": {"$avg": "$total_duration"}
                    }
                }
            ]

            result = list(self.collection.aggregate(pipeline))

            if result:
                stats = result[0]
                return {
                    "total_tests": stats.get("total_tests", 0),
                    "successful_tests": stats.get("successful_tests", 0),
                    "failed_tests": stats.get("failed_tests", 0),
                    "success_rate": (stats.get("successful_tests", 0) / stats.get("total_tests", 1)) * 100,
                    "avg_duration": stats.get("avg_duration", 0),
                    "period_days": days
                }
            else:
                return {
                    "total_tests": 0,
                    "successful_tests": 0,
                    "failed_tests": 0,
                    "success_rate": 0,
                    "avg_duration": 0,
                    "period_days": days
                }

        except Exception as e:
            print(f"İstatistik hesaplama hatası: {e}")
            return self._get_statistics_from_backup()

    def _get_statistics_from_backup(self) -> Dict:
        """Yedek dosyalarından istatistik hesapla"""
        try:
            total = 0
            successful = 0
            durations = []

            for backup_file in self.backup_dir.glob("test_*.json"):
                try:
                    with open(backup_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        total += 1
                        if data.get("status") == "completed":
                            successful += 1
                        if "total_duration" in data:
                            durations.append(data["total_duration"])
                except:
                    continue

            return {
                "total_tests": total,
                "successful_tests": successful,
                "failed_tests": total - successful,
                "success_rate": (successful / total * 100) if total > 0 else 0,
                "avg_duration": sum(durations) / len(durations) if durations else 0,
                "period_days": 30,
                "source": "backup_files"
            }

        except Exception as e:
            print(f"Yedek istatistik hatası: {e}")
            return {
                "total_tests": 0,
                "successful_tests": 0,
                "failed_tests": 0,
                "success_rate": 0,
                "avg_duration": 0,
                "period_days": 30,
                "source": "error"
            }

    def get_recent_tests(self, limit: int = 10) -> List[Dict]:
        """Son testleri getir"""
        if not self.connected:
            return []

        try:
            return list(
                self.collection.find()
                .sort("start_time", -1)
                .limit(limit)
            )
        except Exception as e:
            print(f"Son testler sorgu hatası: {e}")
            return []

    def update_test_status(self, test_id: str, status: str, **kwargs) -> bool:
        """Test durumunu güncelle"""
        if not self.connected:
            return False

        try:
            update_data = {"status": status, **kwargs}
            result = self.collection.update_one(
                {"_id": test_id},
                {"$set": update_data}
            )
            return result.modified_count > 0

        except Exception as e:
            print(f"Test güncelleme hatası: {e}")
            return False

    def cleanup_old_records(self, days: int = 90) -> int:
        """Eski kayıtları temizle"""
        if not self.connected:
            return 0

        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            result = self.collection.delete_many({
                "start_time": {"$lt": cutoff_date.isoformat()}
            })
            return result.deleted_count

        except Exception as e:
            print(f"Kayıt temizleme hatası: {e}")
            return 0

    def export_to_json(self, output_file: str, query: Dict = None) -> bool:
        """Veritabanını JSON'a aktar"""
        if not self.connected:
            return False

        try:
            if query is None:
                query = {}

            data = list(self.collection.find(query))

            # ObjectId'leri string'e çevir
            for item in data:
                if '_id' in item:
                    item['_id'] = str(item['_id'])

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            print(f"Export hatası: {e}")
            return False
