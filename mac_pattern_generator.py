"""
MAC Pattern Generator
Learn patterns from successful MACs and generate similar ones
"""
import re
import random
import logging
from collections import Counter, defaultdict
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)


class MACPatternGenerator:
    """Learn patterns from successful MACs and generate new candidates"""
    
    def __init__(self):
        self.patterns = {
            'prefixes': Counter(),      # First 3 octets (OUI)
            'suffixes': Counter(),      # Last 3 octets
            'full_macs': set(),         # All known MACs
            'sequential': defaultdict(list),  # Sequential patterns
            'gaps': Counter(),          # Common gaps between MACs
        }
        self.total_macs = 0
        logger.info("MAC Pattern Generator initialized")
    
    def learn_from_mac(self, mac: str, success: bool = True):
        """Learn patterns from a MAC address.
        
        Args:
            mac (str): MAC address (e.g., "00:1A:79:12:34:56")
            success (bool): Whether this MAC was successful
        """
        if not success:
            return  # Only learn from successful MACs
        
        mac = mac.upper().replace(':', '')
        
        if len(mac) != 12:
            return
        
        # Extract prefix (OUI) and suffix
        prefix = mac[:6]  # First 3 octets
        suffix = mac[6:]  # Last 3 octets
        
        # Update patterns
        self.patterns['prefixes'][prefix] += 1
        self.patterns['suffixes'][suffix] += 1
        self.patterns['full_macs'].add(mac)
        self.total_macs += 1
        
        # Learn sequential patterns
        mac_int = int(mac, 16)
        self.patterns['sequential'][prefix].append(mac_int)
        
        logger.debug(f"Learned pattern from MAC: {mac}")
    
    def learn_from_mac_list(self, mac_list: List[str]):
        """Learn patterns from a list of successful MACs"""
        for mac in mac_list:
            self.learn_from_mac(mac, success=True)
        
        # Analyze gaps between sequential MACs
        self._analyze_gaps()
        
        logger.info(f"Learned patterns from {len(mac_list)} MACs")
    
    def _analyze_gaps(self):
        """Analyze gaps between sequential MACs to find patterns"""
        for prefix, mac_ints in self.patterns['sequential'].items():
            if len(mac_ints) < 2:
                continue
            
            # Sort MACs
            sorted_macs = sorted(mac_ints)
            
            # Calculate gaps
            for i in range(len(sorted_macs) - 1):
                gap = sorted_macs[i + 1] - sorted_macs[i]
                if gap > 0 and gap < 1000:  # Reasonable gap
                    self.patterns['gaps'][gap] += 1
    
    def generate_candidates(self, count: int = 100, strategy: str = "mixed") -> List[str]:
        """Generate candidate MACs based on learned patterns.
        
        Args:
            count (int): Number of MACs to generate
            strategy (str): Generation strategy:
                - "prefix": Use common prefixes with random suffixes
                - "sequential": Generate sequential MACs around known ones
                - "gap": Use common gap patterns
                - "mixed": Mix of all strategies (default)
        
        Returns:
            List[str]: List of candidate MAC addresses
        """
        if self.total_macs == 0:
            logger.warning("No patterns learned yet, generating random MACs")
            return self._generate_random_macs(count)
        
        candidates = set()
        
        if strategy == "mixed":
            # Mix of strategies
            prefix_count = count // 3
            sequential_count = count // 3
            gap_count = count - prefix_count - sequential_count
            
            candidates.update(self._generate_prefix_based(prefix_count))
            candidates.update(self._generate_sequential(sequential_count))
            candidates.update(self._generate_gap_based(gap_count))
        
        elif strategy == "prefix":
            candidates.update(self._generate_prefix_based(count))
        
        elif strategy == "sequential":
            candidates.update(self._generate_sequential(count))
        
        elif strategy == "gap":
            candidates.update(self._generate_gap_based(count))
        
        # Convert to list and format
        result = []
        for mac_hex in list(candidates)[:count]:
            formatted = ':'.join([mac_hex[i:i+2] for i in range(0, 12, 2)])
            result.append(formatted)
        
        logger.info(f"Generated {len(result)} candidate MACs using '{strategy}' strategy")
        return result
    
    def _generate_prefix_based(self, count: int) -> set:
        """Generate MACs using common prefixes"""
        candidates = set()
        
        # Get top prefixes
        top_prefixes = [prefix for prefix, _ in self.patterns['prefixes'].most_common(10)]
        
        if not top_prefixes:
            return candidates
        
        for _ in range(count):
            # Choose random prefix (weighted by frequency)
            prefix = random.choice(top_prefixes)
            
            # Generate random suffix
            suffix = f"{random.randint(0, 0xFFFFFF):06X}"
            
            mac = prefix + suffix
            
            # Skip if already known
            if mac not in self.patterns['full_macs']:
                candidates.add(mac)
        
        return candidates
    
    def _generate_sequential(self, count: int) -> set:
        """Generate sequential MACs around known ones"""
        candidates = set()
        
        for prefix, mac_ints in self.patterns['sequential'].items():
            if not mac_ints:
                continue
            
            # Get min and max
            min_mac = min(mac_ints)
            max_mac = max(mac_ints)
            
            # Generate MACs in range
            for _ in range(count // len(self.patterns['sequential'])):
                # Random offset from known MAC
                base_mac = random.choice(mac_ints)
                offset = random.randint(-50, 50)
                new_mac = base_mac + offset
                
                # Ensure in reasonable range
                if new_mac >= 0 and new_mac <= 0xFFFFFFFFFFFF:
                    mac_hex = f"{new_mac:012X}"
                    
                    # Skip if already known
                    if mac_hex not in self.patterns['full_macs']:
                        candidates.add(mac_hex)
        
        return candidates
    
    def _generate_gap_based(self, count: int) -> set:
        """Generate MACs using common gap patterns"""
        candidates = set()
        
        # Get top gaps
        top_gaps = [gap for gap, _ in self.patterns['gaps'].most_common(5)]
        
        if not top_gaps:
            return self._generate_sequential(count)
        
        for prefix, mac_ints in self.patterns['sequential'].items():
            if not mac_ints:
                continue
            
            for _ in range(count // len(self.patterns['sequential'])):
                # Choose random known MAC
                base_mac = random.choice(mac_ints)
                
                # Apply random gap
                gap = random.choice(top_gaps)
                direction = random.choice([-1, 1])
                new_mac = base_mac + (gap * direction)
                
                # Ensure valid
                if new_mac >= 0 and new_mac <= 0xFFFFFFFFFFFF:
                    mac_hex = f"{new_mac:012X}"
                    
                    # Skip if already known
                    if mac_hex not in self.patterns['full_macs']:
                        candidates.add(mac_hex)
        
        return candidates
    
    def _generate_random_macs(self, count: int) -> List[str]:
        """Generate random MACs (fallback)"""
        macs = []
        for _ in range(count):
            mac = ':'.join([f"{random.randint(0, 255):02X}" for _ in range(6)])
            macs.append(mac)
        return macs
    
    def get_statistics(self) -> Dict:
        """Get pattern statistics"""
        return {
            'total_macs_learned': self.total_macs,
            'unique_prefixes': len(self.patterns['prefixes']),
            'unique_suffixes': len(self.patterns['suffixes']),
            'top_prefixes': [
                {'prefix': p, 'count': c} 
                for p, c in self.patterns['prefixes'].most_common(5)
            ],
            'top_gaps': [
                {'gap': g, 'count': c} 
                for g, c in self.patterns['gaps'].most_common(5)
            ],
        }
    
    def save_patterns(self, filepath: str):
        """Save learned patterns to file"""
        import json
        
        try:
            data = {
                'prefixes': dict(self.patterns['prefixes']),
                'suffixes': dict(self.patterns['suffixes']),
                'full_macs': list(self.patterns['full_macs']),
                'gaps': dict(self.patterns['gaps']),
                'total_macs': self.total_macs,
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved patterns to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save patterns: {e}")
            return False
    
    def load_patterns(self, filepath: str):
        """Load patterns from file"""
        import json
        import os
        
        try:
            if not os.path.exists(filepath):
                logger.info("No saved patterns file found")
                return False
            
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            self.patterns['prefixes'] = Counter(data.get('prefixes', {}))
            self.patterns['suffixes'] = Counter(data.get('suffixes', {}))
            self.patterns['full_macs'] = set(data.get('full_macs', []))
            self.patterns['gaps'] = Counter(data.get('gaps', {}))
            self.total_macs = data.get('total_macs', 0)
            
            logger.info(f"Loaded patterns from {filepath} ({self.total_macs} MACs)")
            return True
        except Exception as e:
            logger.error(f"Failed to load patterns: {e}")
            return False


# Global pattern generator instance
pattern_generator = MACPatternGenerator()


def get_pattern_generator():
    """Get global pattern generator instance"""
    return pattern_generator
