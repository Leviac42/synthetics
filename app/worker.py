"""Playwright worker for synthetic monitoring"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from .database import get_db_cursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SyntheticWorker:
    """Worker that executes Playwright scripts and captures metrics"""

    def __init__(self):
        self.running = False

    async def execute_monitor(self, monitor_id: int, url: str, timeout_seconds: int = 30) -> Dict[str, Any]:
        """
        Execute a single monitor check using Playwright
        
        Returns dict with metrics: ttfb_ms, dom_content_loaded_ms, page_load_time_ms, har_data
        """
        result = {
            "status": "success",
            "error_message": None,
            "ttfb_ms": None,
            "dom_content_loaded_ms": None,
            "page_load_time_ms": None,
            "har_data": None
        }

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )
                
                context = await browser.new_context(
                    record_har_path=f"/tmp/monitor_{monitor_id}_{datetime.now().timestamp()}.har",
                    record_har_content="omit"
                )
                
                page = await context.new_page()
                
                # Capture performance metrics
                start_time = datetime.now()
                
                # Navigate and capture timing
                try:
                    response = await page.goto(url, timeout=timeout_seconds * 1000, wait_until="load")
                    
                    # TTFB (Time to First Byte) from response timing
                    if response:
                        timing = await response.request.timing()
                        if timing and timing.get('responseStart'):
                            result["ttfb_ms"] = timing['responseStart']
                    
                    # Performance timing API
                    performance_timing = await page.evaluate("""
                        () => {
                            const timing = performance.timing;
                            const navigation = performance.getEntriesByType('navigation')[0];
                            return {
                                domContentLoaded: timing.domContentLoadedEventEnd - timing.navigationStart,
                                pageLoad: timing.loadEventEnd - timing.navigationStart,
                                navigationDomContentLoaded: navigation ? navigation.domContentLoadedEventEnd : null,
                                navigationLoadComplete: navigation ? navigation.loadEventEnd : null
                            };
                        }
                    """)
                    
                    result["dom_content_loaded_ms"] = (
                        performance_timing.get("navigationDomContentLoaded") or 
                        performance_timing.get("domContentLoaded")
                    )
                    result["page_load_time_ms"] = (
                        performance_timing.get("navigationLoadComplete") or 
                        performance_timing.get("pageLoad")
                    )
                    
                except PlaywrightTimeoutError as e:
                    result["status"] = "timeout"
                    result["error_message"] = f"Page load timeout: {str(e)}"
                    logger.warning(f"Monitor {monitor_id} timeout: {e}")
                
                # Close context to save HAR
                await context.close()
                
                # Read HAR data
                try:
                    har_path = context._impl_obj._options.get("recordHarPath")
                    if har_path:
                        with open(har_path, 'r') as f:
                            result["har_data"] = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to read HAR data for monitor {monitor_id}: {e}")
                
                await browser.close()
                
        except Exception as e:
            result["status"] = "error"
            result["error_message"] = str(e)
            logger.error(f"Monitor {monitor_id} execution failed: {e}", exc_info=True)
        
        return result

    async def log_execution(self, monitor_id: int, result: Dict[str, Any]) -> int:
        """Log execution result to database"""
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO execution_logs 
                (monitor_id, started_at, completed_at, status, error_message)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (
                monitor_id,
                datetime.now(),
                datetime.now(),
                result["status"],
                result["error_message"]
            ))
            log_id = cursor.fetchone()["id"]
            
            # Insert performance metrics if available
            if result["status"] == "success" and result.get("ttfb_ms"):
                cursor.execute("""
                    INSERT INTO performance_metrics 
                    (execution_log_id, metric_name, metric_value, recorded_at)
                    VALUES 
                    (%s, 'ttfb_ms', %s, %s),
                    (%s, 'dom_content_loaded_ms', %s, %s),
                    (%s, 'page_load_time_ms', %s, %s)
                """, (
                    log_id, result["ttfb_ms"], datetime.now(),
                    log_id, result["dom_content_loaded_ms"], datetime.now(),
                    log_id, result["page_load_time_ms"], datetime.now()
                ))
                
                # Store HAR data if available
                if result.get("har_data"):
                    cursor.execute("""
                        UPDATE execution_logs 
                        SET har_data = %s
                        WHERE id = %s
                    """, (json.dumps(result["har_data"]), log_id))
            
            return log_id

    async def run_monitor_now(self, monitor_id: int) -> Dict[str, Any]:
        """Execute a specific monitor immediately"""
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT id, name, url, timeout_seconds, enabled
                FROM monitors
                WHERE id = %s
            """, (monitor_id,))
            monitor = cursor.fetchone()
            
            if not monitor:
                return {"status": "error", "error_message": f"Monitor {monitor_id} not found"}
            
            logger.info(f"Executing monitor {monitor_id}: {monitor['name']}")
            result = await self.execute_monitor(
                monitor["id"],
                monitor["url"],
                monitor["timeout_seconds"]
            )
            
            log_id = await self.log_execution(monitor_id, result)
            result["log_id"] = log_id
            
            return result

    async def run_scheduled_monitors(self):
        """Main worker loop - checks for monitors to execute based on schedule"""
        logger.info("Synthetic worker started")
        self.running = True
        
        while self.running:
            try:
                with get_db_cursor() as cursor:
                    # Simple approach: check enabled monitors every minute
                    # In production, use APScheduler or similar for cron scheduling
                    cursor.execute("""
                        SELECT id, name, url, timeout_seconds
                        FROM monitors
                        WHERE enabled = true
                    """)
                    monitors = cursor.fetchall()
                    
                    for monitor in monitors:
                        logger.info(f"Executing scheduled monitor {monitor['id']}: {monitor['name']}")
                        result = await self.execute_monitor(
                            monitor["id"],
                            monitor["url"],
                            monitor["timeout_seconds"]
                        )
                        await self.log_execution(monitor["id"], result)
                
                # Wait before next check (60 seconds)
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                await asyncio.sleep(10)

    def stop(self):
        """Stop the worker"""
        logger.info("Stopping synthetic worker")
        self.running = False


# Global worker instance
worker = SyntheticWorker()
