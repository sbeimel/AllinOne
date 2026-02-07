"""
MAC Scanner Scheduler
Automatic scheduled scanning of MAC lists
"""
import threading
import time
import logging
from datetime import datetime, timedelta
import json
import os

logger = logging.getLogger(__name__)

class ScanScheduler:
    """Schedule automatic MAC scans with cron-like functionality"""
    
    def __init__(self):
        self.jobs = {}
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        self.job_counter = 0
        logger.info("Scan Scheduler initialized")
    
    def add_job(self, portal_url, mac_list, schedule_time="00:00", repeat="daily", 
                enabled=True, name=None, proxy=None, settings=None):
        """Add a scheduled scan job.
        
        Args:
            portal_url (str): Portal URL to scan
            mac_list (list): List of MACs to scan
            schedule_time (str): Time to run (HH:MM format)
            repeat (str): Repeat interval - "once", "daily", "weekly", "hourly"
            enabled (bool): Whether job is enabled
            name (str): Optional job name
            proxy (str): Optional proxy to use
            settings (dict): Optional scanner settings override
        
        Returns:
            str: Job ID
        """
        with self.lock:
            self.job_counter += 1
            job_id = f"job_{self.job_counter}"
            
            job = {
                "id": job_id,
                "name": name or f"Scan {portal_url}",
                "portal_url": portal_url,
                "mac_list": mac_list,
                "schedule_time": schedule_time,
                "repeat": repeat,
                "enabled": enabled,
                "proxy": proxy,
                "settings": settings or {},
                "last_run": None,
                "next_run": self._calculate_next_run(schedule_time, repeat),
                "run_count": 0,
                "success_count": 0,
                "fail_count": 0,
                "created_at": datetime.now().isoformat()
            }
            
            self.jobs[job_id] = job
            logger.info(f"Added scheduled job: {job_id} - {job['name']} (Next run: {job['next_run']})")
            
            return job_id
    
    def remove_job(self, job_id):
        """Remove a scheduled job"""
        with self.lock:
            if job_id in self.jobs:
                job_name = self.jobs[job_id]['name']
                del self.jobs[job_id]
                logger.info(f"Removed scheduled job: {job_id} - {job_name}")
                return True
            return False
    
    def enable_job(self, job_id, enabled=True):
        """Enable or disable a job"""
        with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id]['enabled'] = enabled
                status = "enabled" if enabled else "disabled"
                logger.info(f"Job {job_id} {status}")
                return True
            return False
    
    def get_job(self, job_id):
        """Get job details"""
        with self.lock:
            return self.jobs.get(job_id)
    
    def get_all_jobs(self):
        """Get all jobs"""
        with self.lock:
            return list(self.jobs.values())
    
    def _calculate_next_run(self, schedule_time, repeat):
        """Calculate next run time based on schedule"""
        now = datetime.now()
        
        if repeat == "once":
            # Parse time and set for today or tomorrow
            hour, minute = map(int, schedule_time.split(':'))
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            return next_run.isoformat()
        
        elif repeat == "hourly":
            # Run every hour at minute specified
            minute = int(schedule_time.split(':')[1]) if ':' in schedule_time else 0
            next_run = now.replace(minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(hours=1)
            return next_run.isoformat()
        
        elif repeat == "daily":
            # Run every day at specified time
            hour, minute = map(int, schedule_time.split(':'))
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            return next_run.isoformat()
        
        elif repeat == "weekly":
            # Run every week at specified time
            hour, minute = map(int, schedule_time.split(':'))
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(weeks=1)
            return next_run.isoformat()
        
        return now.isoformat()
    
    def _update_next_run(self, job):
        """Update next run time after job execution"""
        if job['repeat'] == "once":
            # One-time job, disable after running
            job['enabled'] = False
            job['next_run'] = None
        else:
            # Recurring job, calculate next run
            job['next_run'] = self._calculate_next_run(job['schedule_time'], job['repeat'])
    
    def start(self):
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        logger.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Scheduler stopped")
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        while self.running:
            try:
                now = datetime.now()
                
                with self.lock:
                    for job_id, job in list(self.jobs.items()):
                        # Skip disabled jobs
                        if not job['enabled']:
                            continue
                        
                        # Skip if no next_run set
                        if not job['next_run']:
                            continue
                        
                        # Check if it's time to run
                        next_run = datetime.fromisoformat(job['next_run'])
                        if now >= next_run:
                            # Run job in separate thread to avoid blocking
                            threading.Thread(
                                target=self._execute_job,
                                args=(job,),
                                daemon=True
                            ).start()
                
                # Sleep for 30 seconds before next check
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)  # Wait longer on error
    
    def _execute_job(self, job):
        """Execute a scheduled job"""
        job_id = job['id']
        job_name = job['name']
        
        logger.info(f"Executing scheduled job: {job_id} - {job_name}")
        
        try:
            # Import scanner here to avoid circular imports
            import scanner
            
            # Update job stats
            with self.lock:
                job['last_run'] = datetime.now().isoformat()
                job['run_count'] += 1
            
            # Merge job settings with defaults
            settings = scanner.get_scanner_settings()
            settings.update(job.get('settings', {}))
            
            # Start scan
            attack_id = scanner.start_attack(
                portal_url=job['portal_url'],
                mac_list=job['mac_list'],
                proxy=job.get('proxy'),
                settings=settings
            )
            
            logger.info(f"Scheduled job {job_id} started scan: {attack_id}")
            
            # Update success count
            with self.lock:
                job['success_count'] += 1
                self._update_next_run(job)
            
        except Exception as e:
            logger.error(f"Failed to execute scheduled job {job_id}: {e}")
            
            # Update fail count
            with self.lock:
                job['fail_count'] += 1
                self._update_next_run(job)
    
    def save_jobs(self, filepath):
        """Save jobs to file"""
        try:
            with self.lock:
                jobs_data = list(self.jobs.values())
            
            with open(filepath, 'w') as f:
                json.dump(jobs_data, f, indent=2)
            
            logger.info(f"Saved {len(jobs_data)} scheduled jobs to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save jobs: {e}")
            return False
    
    def load_jobs(self, filepath):
        """Load jobs from file"""
        try:
            if not os.path.exists(filepath):
                logger.info("No saved jobs file found")
                return False
            
            with open(filepath, 'r') as f:
                jobs_data = json.load(f)
            
            with self.lock:
                self.jobs.clear()
                for job in jobs_data:
                    job_id = job['id']
                    self.jobs[job_id] = job
                    # Update job counter
                    job_num = int(job_id.split('_')[1])
                    self.job_counter = max(self.job_counter, job_num)
            
            logger.info(f"Loaded {len(jobs_data)} scheduled jobs from {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to load jobs: {e}")
            return False


# Global scheduler instance
scheduler = ScanScheduler()


def get_scheduler():
    """Get global scheduler instance"""
    return scheduler
