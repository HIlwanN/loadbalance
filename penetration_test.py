import requests
import time
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
import queue
import os

class LoadBalancerPenTest:
    def __init__(self, base_url="http://localhost:80"):
        self.base_url = base_url
        self.monitoring_url = self._get_monitoring_url()
        self.endpoints = {
            "round-robin": "/round-robin/",
            "least-conn": "/least-conn/",
            "weighted-least-conn": "/weighted-least-conn/",
            "ip-hash": "/ip-hash/"
        }
        self.results = {}
        self.server_responses = {
            "web1": 0,
            "web2": 0,
            "web3": 0
        }

    def _get_monitoring_url(self):
        """Read monitoring server ports from file"""
        try:
            # Assuming server_ports.json is in the directory above monitoring_server.py
            # Adjust path if necessary
            script_dir = os.path.dirname(os.path.abspath(__file__))
            ports_file_path = os.path.join(script_dir, 'monitoring', 'server_ports.json')
            
            # Fallback if script_dir is LoadBalancer root and server_ports.json is in monitoring/
            if not os.path.exists(ports_file_path):
                 ports_file_path = os.path.join(script_dir, 'server_ports.json')

            with open(ports_file_path, 'r') as f:
                config = json.load(f)
                return f"http://localhost:{config['http_port']}/monitoring"
        except FileNotFoundError:
            print("Error: server_ports.json not found. Make sure monitoring_server.py is running.")
            return None
        except KeyError:
            print("Error: http_port not found in server_ports.json")
            return None
        except Exception as e:
            print(f"Error reading server_ports.json: {e}")
            return None

    def send_to_monitoring(self, data):
        """Send test data to monitoring dashboard"""
        if not self.monitoring_url:
            print("Monitoring URL not available.")
            return
        try:
            requests.post(f"{self.monitoring_url}/update", json=data)
        except Exception as e:
            print(f"Error sending data to monitoring: {e}")

    def single_request_test(self, endpoint):
        """Test single request to each endpoint"""
        print(f"\nTesting single request to {endpoint}...")
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}{self.endpoints[endpoint]}")
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            if response.status_code == 200:
                print(f"Success! Response time: {response_time:.2f}ms")
                # Extract server info from response
                server = None
                if "Web Server 1" in response.text:
                    self.server_responses["web1"] += 1
                    server = "web1"
                elif "Web Server 2" in response.text:
                    self.server_responses["web2"] += 1
                    server = "web2"
                elif "Web Server 3" in response.text:
                    self.server_responses["web3"] += 1
                    server = "web3"

                # Send data to monitoring
                self.send_to_monitoring({
                    "type": "request",
                    "endpoint": endpoint,
                    "server": server,
                    "response_time": response_time,
                    "status": "success"
                })
                
                return response_time
            else:
                print(f"Failed! Status code: {response.status_code}")
                self.send_to_monitoring({
                    "type": "request",
                    "endpoint": endpoint,
                    "status": "failed",
                    "status_code": response.status_code
                })
        except Exception as e:
            print(f"Error: {str(e)}")
            self.send_to_monitoring({
                "type": "request",
                "endpoint": endpoint,
                "status": "error",
                "error": str(e)
            })
        return None

    def load_test(self, endpoint, num_requests=100, concurrent=10):
        """Perform load testing with concurrent requests"""
        print(f"\nLoad testing {endpoint} with {num_requests} requests ({concurrent} concurrent)...")
        response_times = []
        q = queue.Queue()
        
        def worker():
            while True:
                try:
                    response_time = self.single_request_test(endpoint)
                    if response_time is not None:
                        q.put(response_time)
                except queue.Empty:
                    break
        
        # Create and start threads
        threads = []
        for _ in range(concurrent):
            t = threading.Thread(target=worker)
            t.start()
            threads.append(t)
        
        # Wait for all requests to complete
        for _ in range(num_requests):
            try:
                response_time = q.get(timeout=5)
                response_times.append(response_time)
            except queue.Empty:
                break
        
        # Wait for all threads to finish
        for t in threads:
            t.join()
        
        if response_times:
            avg_time = statistics.mean(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            
            # Send load test results to monitoring
            self.send_to_monitoring({
                "type": "load_test_results",
                "endpoint": endpoint,
                "avg_time": avg_time,
                "max_time": max_time,
                "min_time": min_time,
                "total_requests": len(response_times)
            })
            
            print(f"Results for {endpoint}:")
            print(f"Average response time: {avg_time:.2f}ms")
            print(f"Max response time: {max_time:.2f}ms")
            print(f"Min response time: {min_time:.2f}ms")
            self.results[endpoint] = {
                "avg": avg_time,
                "max": max_time,
                "min": min_time
            }

    def stress_test(self, endpoint, duration=10):
        """Perform stress testing for a specified duration"""
        print(f"\nStress testing {endpoint} for {duration} seconds...")
        start_time = time.time()
        total_requests = 0
        errors = 0
        response_times = []
        
        while time.time() - start_time < duration:
            try:
                response_time = self.single_request_test(endpoint)
                if response_time is not None:
                    total_requests += 1
                    response_times.append(response_time)
                else:
                    errors += 1
            except Exception as e:
                errors += 1
                print(f"Error during stress test: {e}")
        
        return {
            "total_requests": total_requests,
            "errors": errors,
            "requests_per_second": total_requests / duration,
            "response_times": response_times
        }

    def save_results(self):
        """Save test results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results = {
            "load_balancing_results": self.results,
            "server_distribution": self.server_responses,
            "timestamp": timestamp
        }
        
        filename = f'test_results_{timestamp}.json'
        with open(filename, 'w') as f:
            json.dump(results, f, indent=4)
        print(f"\nResults saved to {filename}")

    def run_all_tests(self):
        """Run all penetration tests"""
        print("Starting comprehensive penetration testing...")
        
        # Test each endpoint
        for endpoint in self.endpoints:
            print(f"\n{'='*50}")
            print(f"Testing {endpoint}")
            print(f"{'='*50}")
            
            # Single request test
            self.single_request_test(endpoint)
            
            # Load test
            self.load_test(endpoint, num_requests=100, concurrent=10)
            
            # Stress test
            stress_results = self.stress_test(endpoint, duration=10)
            print(f"Stress test results for {endpoint}:")
            print(f"Total requests: {stress_results['total_requests']}")
            print(f"Errors: {stress_results['errors']}")
            print(f"Requests per second: {stress_results['requests_per_second']:.2f}")
            
            time.sleep(1)  # Brief pause between endpoints

        # Save results
        self.save_results()

if __name__ == "__main__":
    # Create and run penetration tests
    pen_test = LoadBalancerPenTest()
    pen_test.run_all_tests() 