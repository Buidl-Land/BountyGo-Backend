"""
Performance and Stress Tests
性能和压力测试
"""
import pytest
import asyncio
import time
import psutil
import os
from unittest.mock import patch, AsyncMock, MagicMock
from concurrent.futures import ThreadPoolExecutor
import statistics

from app.agent.smart_coordinator import SmartCoordinator, UserInput
from app.agent.preference_manager import PreferenceManager
from app.agent.input_analyzer import InputAnalyzer
from app.agent.agent_orchestrator import AgentOrchestrator
from tests.test_mocks import TestDataFactory, MockConfigManager, MockAgent


class TestPerformanceMetrics:
    """Performance metrics and benchmarking tests"""
    
    @pytest.fixture
    async def setup_performance_coordinator(self):
        """Setup coordinator optimized for performance testing"""
        coordinator = SmartCoordinator()
        
        # Use memory-based preference manager for speed
        coordinator.preference_manager = PreferenceManager(storage_backend="memory")
        await coordinator.preference_manager.initialize()
        
        # Mock orchestrator with fast responses
        coordinator.agent_orchestrator = MagicMock()
        coordinator.agent_orchestrator._initialized = True
        
        async def fast_execute_workflow(*args, **kwargs):
            # Simulate minimal processing time
            await asyncio.sleep(0.001)
            return TestDataFactory.create_workflow_result(
                success=True,
                task_info=TestDataFactory.create_task_info(),
                processing_time=0.001
            )
        
        coordinator.agent_orchestrator.execute_workflow = fast_execute_workflow
        
        return coordinator
    
    @pytest.mark.asyncio
    async def test_single_request_latency(self, setup_performance_coordinator):
        """Test single request latency"""
        coordinator = await setup_performance_coordinator
        
        # Warm up
        warm_up_input = UserInput.create("https://warmup.com", "warmup_user")
        await coordinator.process_user_input(warm_up_input)
        
        # Measure latency for different input types
        test_cases = [
            ("URL", "https://performance-test.com"),
            ("Text", "Analyze this text content"),
            ("Preference", "设置输出格式为JSON"),
            ("Status", "系统状态如何？")
        ]
        
        latencies = {}
        
        for test_name, input_text in test_cases:
            times = []
            
            # Run 10 iterations for each test case
            for i in range(10):
                user_input = UserInput.create(input_text, f"perf_user_{i}")
                
                start_time = time.perf_counter()
                result = await coordinator.process_user_input(user_input)
                end_time = time.perf_counter()
                
                assert result.success is True
                times.append(end_time - start_time)
            
            latencies[test_name] = {
                "avg": statistics.mean(times),
                "min": min(times),
                "max": max(times),
                "p95": statistics.quantiles(times, n=20)[18]  # 95th percentile
            }
        
        # Verify performance requirements
        for test_name, metrics in latencies.items():
            assert metrics["avg"] < 0.1, f"{test_name} average latency too high: {metrics['avg']}"
            assert metrics["p95"] < 0.2, f"{test_name} P95 latency too high: {metrics['p95']}"
            
        print(f"Latency metrics: {latencies}")
    
    @pytest.mark.asyncio
    async def test_throughput_capacity(self, setup_performance_coordinator):
        """Test system throughput capacity"""
        coordinator = await setup_performance_coordinator
        
        # Test different concurrency levels
        concurrency_levels = [1, 5, 10, 20, 50]
        throughput_results = {}
        
        for concurrency in concurrency_levels:
            async def process_batch():
                tasks = []
                for i in range(concurrency):
                    user_input = UserInput.create(
                        f"https://throughput-test-{i}.com", 
                        f"user_{i}"
                    )
                    task = coordinator.process_user_input(user_input)
                    tasks.append(task)
                
                start_time = time.perf_counter()
                results = await asyncio.gather(*tasks)
                end_time = time.perf_counter()
                
                return results, end_time - start_time
            
            # Run multiple batches to get average
            batch_times = []
            total_successful = 0
            
            for batch in range(5):
                results, batch_time = await process_batch()
                batch_times.append(batch_time)
                total_successful += sum(1 for r in results if r.success)
            
            avg_batch_time = statistics.mean(batch_times)
            requests_per_second = (concurrency * 5) / sum(batch_times)
            success_rate = total_successful / (concurrency * 5)
            
            throughput_results[concurrency] = {
                "rps": requests_per_second,
                "avg_batch_time": avg_batch_time,
                "success_rate": success_rate
            }
        
        # Verify throughput requirements
        for concurrency, metrics in throughput_results.items():
            assert metrics["success_rate"] >= 0.95, f"Success rate too low at concurrency {concurrency}"
            assert metrics["rps"] > 0, f"Zero throughput at concurrency {concurrency}"
        
        # Verify throughput scales reasonably
        assert throughput_results[10]["rps"] > throughput_results[1]["rps"]
        
        print(f"Throughput results: {throughput_results}")
    
    @pytest.mark.asyncio
    async def test_memory_usage_patterns(self, setup_performance_coordinator):
        """Test memory usage patterns under load"""
        coordinator = await setup_performance_coordinator
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        memory_samples = [initial_memory]
        
        # Process requests while monitoring memory
        for batch in range(10):
            # Process a batch of requests
            tasks = []
            for i in range(20):
                user_input = UserInput.create(
                    f"Memory test batch {batch} request {i}",
                    f"memory_user_{batch}_{i}"
                )
                tasks.append(coordinator.process_user_input(user_input))
            
            results = await asyncio.gather(*tasks)
            
            # Sample memory usage
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append(current_memory)
            
            # Verify all requests succeeded
            successful = sum(1 for r in results if r.success)
            assert successful >= 18  # 90% success rate
        
        final_memory = memory_samples[-1]
        memory_growth = final_memory - initial_memory
        max_memory = max(memory_samples)
        
        # Verify memory usage is reasonable
        assert memory_growth < 50, f"Memory growth too high: {memory_growth}MB"
        assert max_memory < initial_memory + 100, f"Peak memory too high: {max_memory}MB"
        
        print(f"Memory usage - Initial: {initial_memory:.1f}MB, Final: {final_memory:.1f}MB, Growth: {memory_growth:.1f}MB")
    
    @pytest.mark.asyncio
    async def test_cpu_usage_efficiency(self, setup_performance_coordinator):
        """Test CPU usage efficiency"""
        coordinator = await setup_performance_coordinator
        
        # Monitor CPU usage during processing
        cpu_samples = []
        
        async def monitor_cpu():
            for _ in range(20):  # Monitor for 2 seconds
                cpu_percent = psutil.cpu_percent(interval=0.1)
                cpu_samples.append(cpu_percent)
        
        async def process_load():
            tasks = []
            for i in range(100):
                user_input = UserInput.create(
                    f"CPU test request {i}",
                    f"cpu_user_{i}"
                )
                tasks.append(coordinator.process_user_input(user_input))
            
            results = await asyncio.gather(*tasks)
            return results
        
        # Run CPU monitoring and processing concurrently
        monitor_task = asyncio.create_task(monitor_cpu())
        process_task = asyncio.create_task(process_load())
        
        results = await process_task
        await monitor_task
        
        # Analyze CPU usage
        avg_cpu = statistics.mean(cpu_samples)
        max_cpu = max(cpu_samples)
        
        # Verify processing succeeded
        successful = sum(1 for r in results if r.success)
        assert successful >= 95  # 95% success rate
        
        # Verify CPU usage is reasonable (not too high, not too low)
        assert avg_cpu < 80, f"Average CPU usage too high: {avg_cpu}%"
        assert max_cpu < 95, f"Peak CPU usage too high: {max_cpu}%"
        
        print(f"CPU usage - Average: {avg_cpu:.1f}%, Peak: {max_cpu:.1f}%")


class TestStressScenarios:
    """Stress testing scenarios"""
    
    @pytest.fixture
    async def setup_stress_coordinator(self):
        """Setup coordinator for stress testing"""
        coordinator = SmartCoordinator()
        
        # Use memory storage for speed
        coordinator.preference_manager = PreferenceManager(storage_backend="memory")
        await coordinator.preference_manager.initialize()
        
        # Mock orchestrator with variable response times
        coordinator.agent_orchestrator = MagicMock()
        coordinator.agent_orchestrator._initialized = True
        
        async def variable_execute_workflow(*args, **kwargs):
            # Simulate variable processing time (0.001 to 0.01 seconds)
            import random
            await asyncio.sleep(random.uniform(0.001, 0.01))
            
            # Occasionally fail to test error handling
            if random.random() < 0.05:  # 5% failure rate
                return TestDataFactory.create_workflow_result(
                    success=False,
                    error_message="Simulated failure"
                )
            
            return TestDataFactory.create_workflow_result(
                success=True,
                task_info=TestDataFactory.create_task_info()
            )
        
        coordinator.agent_orchestrator.execute_workflow = variable_execute_workflow
        
        return coordinator
    
    @pytest.mark.asyncio
    async def test_sustained_load_stress(self, setup_stress_coordinator):
        """Test sustained load over time"""
        coordinator = await setup_stress_coordinator
        
        # Run sustained load for 30 seconds
        duration = 30  # seconds
        requests_per_second = 10
        
        start_time = time.time()
        all_results = []
        
        async def generate_load():
            request_count = 0
            while time.time() - start_time < duration:
                batch_start = time.time()
                
                # Generate batch of requests
                tasks = []
                for i in range(requests_per_second):
                    user_input = UserInput.create(
                        f"Sustained load request {request_count}",
                        f"stress_user_{request_count % 100}"  # Cycle through 100 users
                    )
                    tasks.append(coordinator.process_user_input(user_input))
                    request_count += 1
                
                # Process batch
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                all_results.extend(batch_results)
                
                # Wait for next second
                elapsed = time.time() - batch_start
                if elapsed < 1.0:
                    await asyncio.sleep(1.0 - elapsed)
        
        await generate_load()
        
        # Analyze results
        successful_results = [r for r in all_results if hasattr(r, 'success') and r.success]
        failed_results = [r for r in all_results if hasattr(r, 'success') and not r.success]
        exceptions = [r for r in all_results if isinstance(r, Exception)]
        
        total_requests = len(all_results)
        success_rate = len(successful_results) / total_requests
        
        # Verify system handled sustained load
        assert total_requests >= duration * requests_per_second * 0.8  # At least 80% of expected requests
        assert success_rate >= 0.90  # At least 90% success rate
        assert len(exceptions) < total_requests * 0.05  # Less than 5% exceptions
        
        print(f"Sustained load - Total: {total_requests}, Success: {success_rate:.2%}, Exceptions: {len(exceptions)}")
    
    @pytest.mark.asyncio
    async def test_burst_load_stress(self, setup_stress_coordinator):
        """Test burst load handling"""
        coordinator = await setup_stress_coordinator
        
        # Test increasing burst sizes
        burst_sizes = [50, 100, 200, 500]
        burst_results = {}
        
        for burst_size in burst_sizes:
            # Generate burst
            tasks = []
            for i in range(burst_size):
                user_input = UserInput.create(
                    f"Burst test {burst_size} request {i}",
                    f"burst_user_{i}"
                )
                tasks.append(coordinator.process_user_input(user_input))
            
            # Process burst and measure time
            start_time = time.perf_counter()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.perf_counter()
            
            # Analyze burst results
            successful = sum(1 for r in results if hasattr(r, 'success') and r.success)
            failed = sum(1 for r in results if hasattr(r, 'success') and not r.success)
            exceptions = sum(1 for r in results if isinstance(r, Exception))
            
            burst_results[burst_size] = {
                "total_time": end_time - start_time,
                "success_rate": successful / burst_size,
                "failed_count": failed,
                "exception_count": exceptions,
                "rps": burst_size / (end_time - start_time)
            }
        
        # Verify burst handling
        for burst_size, metrics in burst_results.items():
            assert metrics["success_rate"] >= 0.85, f"Success rate too low for burst {burst_size}"
            assert metrics["exception_count"] < burst_size * 0.1, f"Too many exceptions for burst {burst_size}"
            assert metrics["total_time"] < 30, f"Burst {burst_size} took too long: {metrics['total_time']}s"
        
        print(f"Burst results: {burst_results}")
    
    @pytest.mark.asyncio
    async def test_memory_pressure_stress(self, setup_stress_coordinator):
        """Test behavior under memory pressure"""
        coordinator = await setup_stress_coordinator
        
        # Create many users to test memory management
        num_users = 1000
        requests_per_user = 10
        
        # Process requests for many users
        all_tasks = []
        for user_id in range(num_users):
            for request_id in range(requests_per_user):
                user_input = UserInput.create(
                    f"Memory pressure test user {user_id} request {request_id}",
                    f"memory_user_{user_id}"
                )
                all_tasks.append(coordinator.process_user_input(user_input))
        
        # Process in batches to avoid overwhelming the system
        batch_size = 100
        all_results = []
        
        for i in range(0, len(all_tasks), batch_size):
            batch = all_tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            all_results.extend(batch_results)
            
            # Small delay between batches
            await asyncio.sleep(0.1)
        
        # Analyze memory pressure results
        successful = sum(1 for r in all_results if hasattr(r, 'success') and r.success)
        total_requests = len(all_results)
        success_rate = successful / total_requests
        
        # Verify system handled memory pressure
        assert success_rate >= 0.80, f"Success rate too low under memory pressure: {success_rate}"
        
        # Verify interaction history is properly managed
        sample_user_history = coordinator.preference_manager.get_user_interaction_history("memory_user_0")
        assert len(sample_user_history) <= 100, "Interaction history not properly limited"
        
        # Verify system is still responsive
        final_input = UserInput.create("Final test after memory pressure", "final_user")
        final_result = await coordinator.process_user_input(final_input)
        assert final_result.success is True
        
        print(f"Memory pressure - Total: {total_requests}, Success: {success_rate:.2%}")
    
    @pytest.mark.asyncio
    async def test_error_cascade_resilience(self, setup_stress_coordinator):
        """Test resilience to error cascades"""
        coordinator = await setup_stress_coordinator
        
        # Mock orchestrator to simulate cascading failures
        failure_count = 0
        
        async def cascading_failure_workflow(*args, **kwargs):
            nonlocal failure_count
            
            # Simulate increasing failure rate
            failure_rate = min(0.5, failure_count * 0.01)  # Up to 50% failure rate
            
            if failure_count < 100:  # First 100 requests
                failure_count += 1
                
                if failure_count % 10 == 0:  # Every 10th request fails
                    return TestDataFactory.create_workflow_result(
                        success=False,
                        error_message=f"Cascading failure {failure_count}"
                    )
            
            # Simulate recovery after initial failures
            await asyncio.sleep(0.001)
            return TestDataFactory.create_workflow_result(
                success=True,
                task_info=TestDataFactory.create_task_info()
            )
        
        coordinator.agent_orchestrator.execute_workflow = cascading_failure_workflow
        
        # Process requests during failure cascade
        results = []
        for i in range(200):
            user_input = UserInput.create(f"Cascade test {i}", f"cascade_user_{i}")
            result = await coordinator.process_user_input(user_input)
            results.append(result)
        
        # Analyze cascade resilience
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        # Verify system recovered from cascade
        first_half_success = sum(1 for r in results[:100] if r.success)
        second_half_success = sum(1 for r in results[100:] if r.success)
        
        assert first_half_success >= 80, "System didn't handle initial failures well"
        assert second_half_success >= 95, "System didn't recover from cascade"
        
        # Verify overall resilience
        overall_success_rate = len(successful_results) / len(results)
        assert overall_success_rate >= 0.85, f"Overall success rate too low: {overall_success_rate}"
        
        print(f"Cascade resilience - First half: {first_half_success}/100, Second half: {second_half_success}/100")


class TestScalabilityLimits:
    """Test system scalability limits"""
    
    @pytest.mark.asyncio
    async def test_concurrent_user_limit(self):
        """Test maximum concurrent users"""
        coordinator = SmartCoordinator()
        
        # Setup minimal system
        coordinator.preference_manager = PreferenceManager(storage_backend="memory")
        await coordinator.preference_manager.initialize()
        
        coordinator.agent_orchestrator = MagicMock()
        coordinator.agent_orchestrator._initialized = True
        coordinator.agent_orchestrator.execute_workflow = AsyncMock(
            return_value=TestDataFactory.create_workflow_result(success=True)
        )
        
        # Test increasing numbers of concurrent users
        user_counts = [100, 500, 1000, 2000]
        scalability_results = {}
        
        for user_count in user_counts:
            try:
                # Create concurrent requests from different users
                tasks = []
                for user_id in range(user_count):
                    user_input = UserInput.create(
                        f"Scalability test from user {user_id}",
                        f"scale_user_{user_id}"
                    )
                    tasks.append(coordinator.process_user_input(user_input))
                
                # Process with timeout
                start_time = time.perf_counter()
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=60.0  # 60 second timeout
                )
                end_time = time.perf_counter()
                
                # Analyze results
                successful = sum(1 for r in results if hasattr(r, 'success') and r.success)
                success_rate = successful / user_count
                processing_time = end_time - start_time
                
                scalability_results[user_count] = {
                    "success_rate": success_rate,
                    "processing_time": processing_time,
                    "rps": user_count / processing_time,
                    "completed": True
                }
                
                # If success rate drops too low, we've found the limit
                if success_rate < 0.8:
                    break
                    
            except asyncio.TimeoutError:
                scalability_results[user_count] = {
                    "success_rate": 0.0,
                    "processing_time": 60.0,
                    "rps": 0.0,
                    "completed": False,
                    "timeout": True
                }
                break
            except Exception as e:
                scalability_results[user_count] = {
                    "success_rate": 0.0,
                    "processing_time": 0.0,
                    "rps": 0.0,
                    "completed": False,
                    "error": str(e)
                }
                break
        
        # Verify scalability
        successful_counts = [count for count, result in scalability_results.items() 
                           if result.get("success_rate", 0) >= 0.8]
        
        assert len(successful_counts) > 0, "System couldn't handle even minimal concurrent users"
        max_users = max(successful_counts)
        assert max_users >= 100, f"System should handle at least 100 concurrent users, got {max_users}"
        
        print(f"Scalability results: {scalability_results}")
        print(f"Maximum concurrent users with 80% success rate: {max_users}")
    
    @pytest.mark.asyncio
    async def test_request_rate_limit(self):
        """Test maximum request rate"""
        coordinator = SmartCoordinator()
        
        # Setup fast system
        coordinator.preference_manager = PreferenceManager(storage_backend="memory")
        await coordinator.preference_manager.initialize()
        
        coordinator.agent_orchestrator = MagicMock()
        coordinator.agent_orchestrator._initialized = True
        coordinator.agent_orchestrator.execute_workflow = AsyncMock(
            return_value=TestDataFactory.create_workflow_result(success=True)
        )
        
        # Test increasing request rates
        rates = [10, 50, 100, 200, 500]  # requests per second
        rate_results = {}
        
        for target_rate in rates:
            try:
                duration = 5  # seconds
                total_requests = target_rate * duration
                
                async def generate_requests():
                    tasks = []
                    start_time = time.time()
                    
                    for i in range(total_requests):
                        user_input = UserInput.create(
                            f"Rate test {target_rate}rps request {i}",
                            f"rate_user_{i % 10}"
                        )
                        tasks.append(coordinator.process_user_input(user_input))
                        
                        # Control rate
                        expected_time = start_time + (i + 1) / target_rate
                        current_time = time.time()
                        if current_time < expected_time:
                            await asyncio.sleep(expected_time - current_time)
                    
                    return await asyncio.gather(*tasks, return_exceptions=True)
                
                # Execute rate test
                start_time = time.perf_counter()
                results = await asyncio.wait_for(generate_requests(), timeout=duration + 10)
                end_time = time.perf_counter()
                
                # Analyze rate results
                successful = sum(1 for r in results if hasattr(r, 'success') and r.success)
                actual_rate = len(results) / (end_time - start_time)
                success_rate = successful / len(results)
                
                rate_results[target_rate] = {
                    "actual_rate": actual_rate,
                    "success_rate": success_rate,
                    "total_requests": len(results),
                    "completed": True
                }
                
                # If we can't maintain the rate or success drops, we've found the limit
                if actual_rate < target_rate * 0.8 or success_rate < 0.9:
                    break
                    
            except asyncio.TimeoutError:
                rate_results[target_rate] = {
                    "actual_rate": 0.0,
                    "success_rate": 0.0,
                    "total_requests": 0,
                    "completed": False,
                    "timeout": True
                }
                break
            except Exception as e:
                rate_results[target_rate] = {
                    "actual_rate": 0.0,
                    "success_rate": 0.0,
                    "total_requests": 0,
                    "completed": False,
                    "error": str(e)
                }
                break
        
        # Verify rate handling
        successful_rates = [rate for rate, result in rate_results.items() 
                          if result.get("success_rate", 0) >= 0.9 and result.get("actual_rate", 0) >= rate * 0.8]
        
        assert len(successful_rates) > 0, "System couldn't handle even minimal request rates"
        max_rate = max(successful_rates)
        assert max_rate >= 10, f"System should handle at least 10 rps, got {max_rate}"
        
        print(f"Rate limit results: {rate_results}")
        print(f"Maximum sustainable rate: {max_rate} rps")