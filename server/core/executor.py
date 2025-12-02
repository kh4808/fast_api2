# server/core/executor.py - Thread/Process Executor 관리
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Callable, Any
from functools import partial

# ============================================================================
# ✅ CPU 바운드 작업용 Thread Pool (OCR, CEFR 분류 등)
# ============================================================================
# ThreadPoolExecutor: GIL이 있지만 I/O 대기가 있는 작업에 적합
# ProcessPoolExecutor: GIL 우회, 순수 CPU 작업에 적합 (pickle 가능한 객체만)
# ============================================================================

# CPU 코어 수의 2배로 설정 (일반적으로 4-8개)
CPU_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="cpu_worker")

# I/O 바운드 작업용 Thread Pool (파일 I/O 등)
IO_EXECUTOR = ThreadPoolExecutor(max_workers=16, thread_name_prefix="io_worker")


async def run_in_threadpool(func: Callable, *args, **kwargs) -> Any:
    """
    동기 함수를 thread pool에서 비동기로 실행

    Args:
        func: 실행할 동기 함수
        *args, **kwargs: 함수 인자

    Returns:
        함수 실행 결과

    Example:
        result = await run_in_threadpool(cv2.imdecode, np_arr, cv2.IMREAD_COLOR)
    """
    loop = asyncio.get_event_loop()
    if kwargs:
        func = partial(func, **kwargs)
    return await loop.run_in_executor(CPU_EXECUTOR, func, *args)


async def run_io_in_threadpool(func: Callable, *args, **kwargs) -> Any:
    """
    I/O 바운드 동기 함수를 thread pool에서 실행

    Args:
        func: 실행할 I/O 함수
        *args, **kwargs: 함수 인자

    Returns:
        함수 실행 결과

    Example:
        data = await run_io_in_threadpool(file.read)
    """
    loop = asyncio.get_event_loop()
    if kwargs:
        func = partial(func, **kwargs)
    return await loop.run_in_executor(IO_EXECUTOR, func, *args)


def shutdown_executors():
    """서버 종료 시 executor를 정리"""
    print("🔄 Shutting down executors...")
    CPU_EXECUTOR.shutdown(wait=True)
    IO_EXECUTOR.shutdown(wait=True)
    print("✅ Executors shut down successfully")
