#!/usr/bin/env python3
"""
AI8 Architecture - Service Testing Suite
Tests the functionality of all deployed services
"""

import requests
import json
import time
import sys
import subprocess
from typing import Dict, List, Tuple
import psycopg2
import redis
import pymongo
from colorama import init, Fore, Style

# Initialize colorama for colored output
init()

class ServiceTester:
    def __init__(self):
        self.results = {}
        self.failed_tests = []
        
    def log_info(self, message: str):
        print(f"{Fore.BLUE}[INFO]{Style.RESET_ALL} {message}")
        
    def log_success(self, message: str):
        print(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} {message}")
        
    def log_warning(self, message: str):
        print(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} {message}")
        
    def log_error(self, message: str):
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {message}")

    def test_service_health(self, service_name: str, url: str, expected_status: int = 200) -> bool:
        """Test basic HTTP health endpoint"""
        try:
            self.log_info(f"Testing {service_name} health endpoint: {url}")
            response = requests.get(url, timeout=10)
            if response.status_code == expected_status:
                self.log_success(f"{service_name} health check passed")
                return True
            else:
                self.log_error(f"{service_name} health check failed: HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_error(f"{service_name} health check failed: {str(e)}")
            return False

    def test_postgres(self) -> bool:
        """Test PostgreSQL connection and basic operations"""
        try:
            self.log_info("Testing PostgreSQL database connection...")
            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                database="litellm",
                user="llmuser",
                password="change_this_secure_password_now"
            )
            cursor = conn.cursor()
            
            # Test basic query
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            self.log_success(f"PostgreSQL connected successfully: {version[0][:50]}...")
            
            # Test table creation and data insertion
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_table (
                    id SERIAL PRIMARY KEY,
                    test_data VARCHAR(100),
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            
            cursor.execute("INSERT INTO test_table (test_data) VALUES (%s);", ("AI8 Test Data",))
            cursor.execute("SELECT COUNT(*) FROM test_table;")
            count = cursor.fetchone()[0]
            
            self.log_success(f"PostgreSQL write/read test passed. Records in test table: {count}")
            
            # Cleanup
            cursor.execute("DROP TABLE IF EXISTS test_table;")
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
        except Exception as e:
            self.log_error(f"PostgreSQL test failed: {str(e)}")
            return False

    def test_redis(self) -> bool:
        """Test Redis connection and basic operations"""
        try:
            self.log_info("Testing Redis connection...")
            r = redis.Redis(
                host='localhost',
                port=6379,
                password='change_this_redis_password_now',
                decode_responses=True
            )
            
            # Test ping
            if r.ping():
                self.log_success("Redis ping successful")
            else:
                self.log_error("Redis ping failed")
                return False
            
            # Test set/get operations
            test_key = "ai8_test_key"
            test_value = "AI8 Architecture Test"
            
            r.set(test_key, test_value, ex=60)  # Expire in 60 seconds
            retrieved_value = r.get(test_key)
            
            if retrieved_value == test_value:
                self.log_success("Redis set/get operations successful")
            else:
                self.log_error("Redis set/get operations failed")
                return False
            
            # Test list operations
            list_key = "ai8_test_list"
            r.lpush(list_key, "item1", "item2", "item3")
            list_length = r.llen(list_key)
            
            if list_length == 3:
                self.log_success("Redis list operations successful")
            else:
                self.log_error("Redis list operations failed")
                return False
            
            # Cleanup
            r.delete(test_key, list_key)
            
            return True
        except Exception as e:
            self.log_error(f"Redis test failed: {str(e)}")
            return False

    def test_mongodb(self) -> bool:
        """Test MongoDB connection and basic operations"""
        try:
            self.log_info("Testing MongoDB connection...")
            client = pymongo.MongoClient(
                "mongodb://admin:change_this_mongo_password_now@localhost:27017/"
            )
            
            # Test connection
            client.admin.command('ismaster')
            self.log_success("MongoDB connection successful")
            
            # Test database and collection operations
            db = client.ai8_test_db
            collection = db.test_collection
            
            # Insert test document
            test_doc = {
                "service": "AI8 Architecture",
                "test_timestamp": time.time(),
                "test_data": {"key1": "value1", "key2": "value2"}
            }
            
            result = collection.insert_one(test_doc)
            self.log_success(f"MongoDB document inserted with ID: {result.inserted_id}")
            
            # Query document
            found_doc = collection.find_one({"_id": result.inserted_id})
            if found_doc and found_doc["service"] == "AI8 Architecture":
                self.log_success("MongoDB query operations successful")
            else:
                self.log_error("MongoDB query operations failed")
                return False
            
            # Update document
            collection.update_one(
                {"_id": result.inserted_id},
                {"$set": {"updated": True}}
            )
            
            # Verify update
            updated_doc = collection.find_one({"_id": result.inserted_id})
            if updated_doc and updated_doc.get("updated") == True:
                self.log_success("MongoDB update operations successful")
            else:
                self.log_error("MongoDB update operations failed")
                return False
            
            # Cleanup
            collection.delete_one({"_id": result.inserted_id})
            client.drop_database("ai8_test_db")
            client.close()
            
            return True
        except Exception as e:
            self.log_error(f"MongoDB test failed: {str(e)}")
            return False

    def test_chroma(self) -> bool:
        """Test ChromaDB vector database operations"""
        try:
            self.log_info("Testing ChromaDB vector database...")
            
            # Test heartbeat
            heartbeat_response = requests.get("http://localhost:8000/api/v1/heartbeat", timeout=10)
            if heartbeat_response.status_code == 200:
                self.log_success("ChromaDB heartbeat successful")
            else:
                self.log_error("ChromaDB heartbeat failed")
                return False
            
            # Test collections list
            collections_response = requests.get("http://localhost:8000/api/v1/collections", timeout=10)
            if collections_response.status_code == 200:
                self.log_success("ChromaDB collections endpoint accessible")
            else:
                self.log_error("ChromaDB collections endpoint failed")
                return False
            
            # Test creating a collection
            collection_data = {
                "name": "ai8_test_collection",
                "metadata": {"test": "true"}
            }
            
            create_response = requests.post(
                "http://localhost:8000/api/v1/collections",
                json=collection_data,
                timeout=10
            )
            
            if create_response.status_code in [200, 201]:
                self.log_success("ChromaDB collection creation successful")
            else:
                self.log_warning(f"ChromaDB collection creation returned status: {create_response.status_code}")
            
            return True
        except Exception as e:
            self.log_error(f"ChromaDB test failed: {str(e)}")
            return False

    def test_qdrant(self) -> bool:
        """Test Qdrant vector database operations"""
        try:
            self.log_info("Testing Qdrant vector database...")
            
            # Test health endpoint
            health_response = requests.get("http://localhost:6333/healthz", timeout=10)
            if health_response.status_code == 200:
                self.log_success("Qdrant health check successful")
            else:
                self.log_error("Qdrant health check failed")
                return False
            
            # Test collections list
            collections_response = requests.get("http://localhost:6333/collections", timeout=10)
            if collections_response.status_code == 200:
                collections = collections_response.json()
                self.log_success(f"Qdrant collections accessible. Found {len(collections.get('result', {}).get('collections', []))} collections")
            else:
                self.log_error("Qdrant collections endpoint failed")
                return False
            
            # Test creating a collection
            collection_config = {
                "vectors": {
                    "size": 128,
                    "distance": "Cosine"
                }
            }
            
            create_response = requests.put(
                "http://localhost:6333/collections/ai8_test_collection",
                json=collection_config,
                timeout=10
            )
            
            if create_response.status_code in [200, 201]:
                self.log_success("Qdrant collection creation successful")
                
                # Test deleting the collection
                delete_response = requests.delete(
                    "http://localhost:6333/collections/ai8_test_collection",
                    timeout=10
                )
                if delete_response.status_code == 200:
                    self.log_success("Qdrant collection deletion successful")
            else:
                self.log_warning(f"Qdrant collection creation returned status: {create_response.status_code}")
            
            return True
        except Exception as e:
            self.log_error(f"Qdrant test failed: {str(e)}")
            return False

    def test_embeddings_service(self) -> bool:
        """Test custom embeddings service"""
        try:
            self.log_info("Testing Embeddings Service...")
            
            # Test health endpoint
            health_response = requests.get("http://localhost:8010/health", timeout=10)
            if health_response.status_code == 200:
                self.log_success("Embeddings Service health check successful")
            else:
                self.log_error("Embeddings Service health check failed")
                return False
            
            # Test embeddings generation
            test_text = "This is a test sentence for AI8 Architecture embeddings service."
            embeddings_data = {
                "text": test_text,
                "model": "default"
            }
            
            embeddings_response = requests.post(
                "http://localhost:8010/embeddings",
                json=embeddings_data,
                timeout=30
            )
            
            if embeddings_response.status_code == 200:
                response_data = embeddings_response.json()
                if "embeddings" in response_data and len(response_data["embeddings"]) > 0:
                    self.log_success(f"Embeddings generation successful. Vector dimension: {len(response_data['embeddings'])}")
                    return True
                else:
                    self.log_error("Embeddings response format invalid")
                    return False
            else:
                self.log_error(f"Embeddings generation failed: HTTP {embeddings_response.status_code}")
                return False
        except Exception as e:
            self.log_error(f"Embeddings Service test failed: {str(e)}")
            return False

    def test_ollama_services(self) -> bool:
        """Test Ollama services"""
        try:
            self.log_info("Testing Ollama services...")
            
            # Test primary GPT OSS service
            try:
                primary_response = requests.get("http://localhost:11601/api/tags", timeout=10)
                if primary_response.status_code == 200:
                    models = primary_response.json()
                    self.log_success(f"Primary Ollama service accessible. Models: {len(models.get('models', []))}")
                else:
                    self.log_warning("Primary Ollama service not responding properly")
            except Exception as e:
                self.log_warning(f"Primary Ollama service test failed: {str(e)}")
            
            # Test secondary DeepSeek service
            try:
                secondary_response = requests.get("http://localhost:11603/api/tags", timeout=10)
                if secondary_response.status_code == 200:
                    models = secondary_response.json()
                    self.log_success(f"Secondary Ollama (DeepSeek) service accessible. Models: {len(models.get('models', []))}")
                else:
                    self.log_warning("Secondary Ollama service not responding properly")
            except Exception as e:
                self.log_warning(f"Secondary Ollama service test failed: {str(e)}")
            
            # Test playground Ollama service
            try:
                playground_response = requests.get("http://localhost:11620/api/tags", timeout=10)
                if playground_response.status_code == 200:
                    models = playground_response.json()
                    self.log_success(f"Playground Ollama service accessible. Models: {len(models.get('models', []))}")
                else:
                    self.log_warning("Playground Ollama service not responding properly")
            except Exception as e:
                self.log_warning(f"Playground Ollama service test failed: {str(e)}")
            
            return True
        except Exception as e:
            self.log_error(f"Ollama services test failed: {str(e)}")
            return False

    def test_openwebui(self) -> bool:
        """Test Open WebUI interface"""
        try:
            self.log_info("Testing Open WebUI interface...")
            
            # Test main interface
            response = requests.get("http://localhost:5151", timeout=10)
            if response.status_code == 200:
                self.log_success("Open WebUI interface accessible")
                return True
            else:
                self.log_error(f"Open WebUI interface failed: HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_error(f"Open WebUI test failed: {str(e)}")
            return False

    def test_monitoring_services(self) -> bool:
        """Test monitoring services (Prometheus, Grafana, GPU Exporter)"""
        try:
            self.log_info("Testing monitoring services...")
            
            # Test Prometheus
            try:
                prometheus_response = requests.get("http://localhost:9091", timeout=10)
                if prometheus_response.status_code == 200:
                    self.log_success("Prometheus monitoring accessible")
                else:
                    self.log_warning("Prometheus monitoring not accessible")
            except Exception as e:
                self.log_warning(f"Prometheus test failed: {str(e)}")
            
            # Test Grafana
            try:
                grafana_response = requests.get("http://localhost:3000", timeout=10)
                if grafana_response.status_code == 200:
                    self.log_success("Grafana dashboard accessible")
                else:
                    self.log_warning("Grafana dashboard not accessible")
            except Exception as e:
                self.log_warning(f"Grafana test failed: {str(e)}")
            
            # Test GPU Exporter
            try:
                gpu_response = requests.get("http://localhost:9835/metrics", timeout=10)
                if gpu_response.status_code == 200:
                    self.log_success("GPU Exporter metrics accessible")
                else:
                    self.log_warning("GPU Exporter metrics not accessible")
            except Exception as e:
                self.log_warning(f"GPU Exporter test failed: {str(e)}")
            
            return True
        except Exception as e:
            self.log_error(f"Monitoring services test failed: {str(e)}")
            return False

    def run_all_tests(self) -> Dict[str, bool]:
        """Run all service tests"""
        print("=" * 80)
        print("AI8 ARCHITECTURE - SERVICE TESTING SUITE")
        print("=" * 80)
        print()
        
        test_results = {}
        
        # Database services
        test_results['postgres'] = self.test_postgres()
        test_results['redis'] = self.test_redis()
        test_results['mongodb'] = self.test_mongodb()
        
        # Vector databases
        test_results['chroma'] = self.test_chroma()
        test_results['qdrant'] = self.test_qdrant()
        
        # AI/ML services
        test_results['embeddings'] = self.test_embeddings_service()
        test_results['ollama'] = self.test_ollama_services()
        
        # Interface services
        test_results['openwebui'] = self.test_openwebui()
        
        # Monitoring services
        test_results['monitoring'] = self.test_monitoring_services()
        
        return test_results

    def print_summary(self, test_results: Dict[str, bool]):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for result in test_results.values() if result)
        total = len(test_results)
        
        for service, result in test_results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{service.upper():<20} {status}")
        
        print("-" * 80)
        print(f"TOTAL: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
        
        if passed == total:
            self.log_success("All tests passed! 🎉")
        else:
            self.log_warning(f"{total - passed} test(s) failed. Check logs above for details.")
        
        return passed == total

def main():
    """Main function"""
    tester = ServiceTester()
    test_results = tester.run_all_tests()
    all_passed = tester.print_summary(test_results)
    
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()