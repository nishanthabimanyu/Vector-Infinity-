
import os
import pandas as pd
import numpy as np
from skyfield.api import load, Loader
from datetime import datetime, timedelta

class OrbitalDataManager:
    def __init__(self, storage_path="solar_system.h5", bsp_path="de441.bsp"):
        # Resolve absolute paths
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # If bsp_path is relative, make it absolute relative to project root
        if not os.path.isabs(bsp_path):
            self.bsp_path = os.path.join(self.base_dir, bsp_path)
        else:
            self.bsp_path = bsp_path
            
        if not os.path.isabs(storage_path):
            self.storage_path = os.path.join(self.base_dir, storage_path)
        else:
            self.storage_path = storage_path
            
        self.ts = load.timescale()
        self.ephemeris = None
        self.is_loaded = False
        self.load_error = None
        self.file_size_mb = 0

    def load_ephemeris(self):
        """Loads the BSP file. Designed to be run in a thread. Returns dict with status."""
        if self.is_loaded: 
            hierarchy, root_id = self.get_bsp_hierarchy()
            return {
                'success': True, 
                'path': self.bsp_path,
                'size_mb': self.file_size_mb,
                'message': 'Already loaded',
                'hierarchy': hierarchy,
                'root_id': root_id
            }
        
        if os.path.exists(self.bsp_path):
            try:
                # Get file size
                self.file_size_mb = os.path.getsize(self.bsp_path) / (1024 * 1024)
                
                # Load ephemeris
                self.ephemeris = load(self.bsp_path)
                self.is_loaded = True
                
                print(f"OrbitalDataManager: Loaded {self.bsp_path} ({self.file_size_mb:.2f} MB)")
                
                # Pre-calculate hierarchy to avoid lag in UI thread
                hierarchy, root_id = self.get_bsp_hierarchy()
                
                return {
                    'success': True,
                    'path': self.bsp_path,
                    'size_mb': self.file_size_mb,
                    'message': f'Successfully loaded DE441 ({self.file_size_mb:.0f} MB)',
                    'hierarchy': hierarchy,
                    'root_id': root_id
                }
            except Exception as e:
                self.load_error = str(e)
                print(f"OrbitalDataManager Error: Failed to load BSP: {e}")
                return {
                    'success': False,
                    'path': self.bsp_path,
                    'size_mb': 0,
                    'message': f'Load failed: {str(e)}',
                    'hierarchy': {},
                    'root_id': None
                }
        else:
            self.load_error = f"File not found: {self.bsp_path}"
            print(f"OrbitalDataManager Warning: BSP file not found at {self.bsp_path}")
            return {
                'success': False,
                'path': self.bsp_path,
                'size_mb': 0,
                'message': f'File not found at: {self.bsp_path}',
                'hierarchy': {},
                'root_id': None
            }

    def generate_hdf5_cache(self, start_date, end_date, step_hours=24, progress_callback=None):
        """
        Generates HDF5 cache from BSP for a range of dates.
        Structure: /planet_name/vectors (Dataframe with Index=Time, Columns=[x,y,z,vx,vy,vz])
        """
        if not self.ephemeris:
            print("OrbitalDataManager: Cannot generate cache without loaded Ephemeris.")
            return

        print(f"OrbitalDataManager: Generating HDF5 Cache from {start_date} to {end_date}...")
        
        t_start = self.ts.from_datetime(start_date)
        t_end = self.ts.from_datetime(end_date)
        
        # Create time range
        # Skyfield time handling for steps
        times = []
        current = start_date
        while current <= end_date:
            times.append(self.ts.from_datetime(current))
            current += timedelta(hours=step_hours)
            
        t_vector = self.ts.from_datetimes([t.utc_datetime() for t in times])

        bodies = {
            'Sun': 'sun',
            'Mercury': 'mercury',
            'Venus': 'venus',
            'Earth': 'earth',
            'Mars': 'mars',
            'Jupiter': 'jupiter barycenter',
            'Saturn': 'saturn barycenter',
            'Uranus': 'uranus barycenter',
            'Neptune': 'neptune barycenter',
            'Pluto': 'pluto barycenter'
        }

        with pd.HDFStore(self.storage_path, mode='w') as store:
            total_bodies = len(bodies)
            for i, (name, kernel_name) in enumerate(bodies.items()):
                try:
                    if progress_callback:
                        progress_callback.emit(int((i / total_bodies) * 100))
                        
                    body = self.ephemeris[kernel_name]
                    # Calculate positions relative to Solar System Barycenter (or Sun?)
                    # DE441 is usually Barycentric. Let's use SSB.
                    # Note: 'de441.bsp' might not have all 'barycenter' names exactly as listed for older BSPs.
                    # Checking validity...
                    
                    # Compute
                    # .at() returns a position object. .position.km returns vectors.
                    # We want Barycentric positions mostly for the 'System View'.
                    # Or Heliocentric? System view usually centers on Sun.
                    # Let's cache Heliocentric (Sun-Centered) vectors for animation simplicity, 
                    # OR Barycentric and let the view decide. Barycentric is more detailed.
                    
                    # Let's perform a relative calculation: Body relative to Sun
                    sun = self.ephemeris['sun']
                    astrometric = sun.at(t_vector).observe(body)
                    pos = astrometric.position.au # Use AU for scale
                    vel = astrometric.velocity.au_per_d # AU per day
                    
                    df = pd.DataFrame({
                        'x': pos[0], 'y': pos[1], 'z': pos[2],
                        'vx': vel[0], 'vy': vel[1], 'vz': vel[2]
                    }, index=[t.utc_datetime() for t in times])
                    
                    store.put(f"{name}/vectors", df)
                    print(f"OrbitalDataManager: Cached {name}")
                    
                except Exception as e:
                    print(f"OrbitalDataManager: Error caching {name}: {e}")
        
        if progress_callback:
            progress_callback.emit(100)
            
        print("OrbitalDataManager: Cache Complete.")

    def get_position(self, body_name, query_time=None):
        """
        Retrieves position of a body at a specific time.
        Priority: HDF5 cache (chunked slicing) -> BSP (via Skyfield).
        """
        if not body_name:
            return None

        # Try HDF5 cache first (Optimized for Speed)
        if os.path.exists(self.storage_path):
            try:
                import h5py
                
                # Normalize body name to lowercase for HDF5 lookup
                hdf_key = body_name.lower().replace(' barycenter', '')
                
                with h5py.File(self.storage_path, 'r') as f:
                    if hdf_key in f:
                        # Get time in Julian Date
                        if query_time is None:
                            from datetime import datetime, timezone
                            query_time = datetime.now(timezone.utc)
                        
                        # Convert to JD (Julian Date)
                        t_jd = self.ts.from_datetime(query_time).tt
                        
                        # OPTIMIZATION: Use binary search to find nearest index
                        # Instead of loading entire 5.5M array, just get metadata
                        # Check bounds first (read only first and last values)
                        n_points = time_dataset.shape[0]
                        if n_points == 0:
                            raise ValueError("HDF5 dataset is empty")
                            
                        t_start = time_dataset[0]
                        t_end = time_dataset[-1]
                        
                        if not (t_start <= t_jd <= t_end):
                            # Out of HDF5 range, fall back to BSP
                            raise ValueError("Time outside HDF5 range")
                        
                        # Binary search to find nearest index
                        # Sample strategy: check every 1000th point to narrow down
                        step = max(1, n_points // 1000)
                        sample_indices = list(range(0, n_points, step)) + [n_points - 1]
                        sample_times = time_dataset[sample_indices]
                        
                        # Find bracketing interval
                        idx_low = 0
                        for i, t_sample in enumerate(sample_times):
                            if t_sample > t_jd:
                                idx_low = max(0, sample_indices[i-1])
                                idx_high = min(n_points - 1, sample_indices[i])
                                break
                        else:
                            idx_low = sample_indices[-2]
                            idx_high = sample_indices[-1]
                        
                        # Refine search in narrowed range
                        refined_times = time_dataset[idx_low:idx_high+1]
                        local_idx = np.searchsorted(refined_times, t_jd)
                        global_idx = idx_low + local_idx
                        
                        # Linear interpolation between two nearest points
                        if global_idx >= n_points - 1:
                            global_idx = n_points - 2
                        
                        idx_a = global_idx
                        idx_b = global_idx + 1
                        
                        # Load ONLY the 2 points we need for interpolation
                        t_a = time_dataset[idx_a]
                        t_b = time_dataset[idx_b]
                        
                        # Interpolation weight
                        alpha = (t_jd - t_a) / (t_b - t_a) if t_b != t_a else 0.0
                        
                        # Load position and velocity for these 2 points only
                        pos_a = f[hdf_key]['position'][idx_a]
                        pos_b = f[hdf_key]['position'][idx_b]
                        vel_a = f[hdf_key]['velocity'][idx_a]
                        vel_b = f[hdf_key]['velocity'][idx_b]
                        
                        # Interpolate
                        pos_result = pos_a + alpha * (pos_b - pos_a)
                        vel_result = vel_a + alpha * (vel_b - vel_a)
                        
                        return {
                            'x': float(pos_result[0]),
                            'y': float(pos_result[1]),
                            'z': float(pos_result[2]),
                            'vx': float(vel_result[0]),
                            'vy': float(vel_result[1]),
                            'vz': float(vel_result[2])
                        }
            except Exception as e:
                # Silent fallback to BSP if HDF5 fails
                pass

        # Fallback: BSP via Skyfield (Always Reliable)
        if not self.ephemeris:
            return None

        try:
            t = self.ts.now() if query_time is None else self.ts.from_datetime(query_time)
            
            # 1. Try direct lookup (best for tree names)
            try:
                target = self.ephemeris[body_name]
            except (KeyError, ValueError, IndexError):
                # 2. Try replacing underscores with spaces (common in NAIF names)
                try:
                    target = self.ephemeris[body_name.replace('_', ' ')]
                except (KeyError, ValueError, IndexError):
                    # 3. Try lower case
                    try:
                        target = self.ephemeris[body_name.lower()]
                    except (KeyError, ValueError, IndexError):
                        # 4. Try upper case
                        try:
                            target = self.ephemeris[body_name.upper()]
                        except (KeyError, ValueError, IndexError):
                            # 5. Check if it's a numeric string (NAIF ID)
                            try:
                                if str(body_name).isdigit():
                                    target = self.ephemeris[int(body_name)]
                                else:
                                    raise KeyError
                            except (KeyError, ValueError, IndexError):
                                print(f"OrbitalDataManager Error: Could not resolve body '{body_name}'")
                                return None

            # Always relative to Sun for "Heliocentric" view
            sun = self.ephemeris['sun']
            
            # Observe
            astrometric = sun.at(t).observe(target)
            
            # Extract
            pos = astrometric.position.au
            vel = astrometric.velocity.au_per_d
            
            return {
                'x': pos[0], 'y': pos[1], 'z': pos[2],
                'vx': vel[0], 'vy': vel[1], 'vz': vel[2]
            }
            
        except Exception as e:
            print(f"OrbitalDataManager Error in get_position('{body_name}'): {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_trajectory(self, body_name):
        """Returns the full cached dataframe for a body."""
        try:
            # Check if file exists to avoid costly open error
            if not os.path.exists(self.storage_path):
                return None
                
            return pd.read_hdf(self.storage_path, key=f"{body_name}/vectors")
        except Exception as e:
            # print(f"HDF5 Read Error: {e}")
            return None

    def get_bsp_hierarchy(self):
        """
        Parses the loaded BSP file components to build a parent-child hierarchy.
        Returns a dict: {node_id: {'name': str, 'children': [child_ids...]}}
        """
        if not self.ephemeris:
            return {}
            
        hierarchy = {}
        names_map = {}
        
        # Build ID -> Name map
        for code, names in self.ephemeris.names().items():
            # Choose the "best" name (longest or first?)
            # Usually the first one is the official NAIF name or similar
            # But sometimes all caps like 'SOLAR_SYSTEM_BARYCENTER'.
            # Let's pick the one that looks most like a title if available, else first.
            best_name = names[0]
            for n in names:
                if not n.isupper(): # Prefer 'Mercury' over 'MERCURY'
                    best_name = n
                    break
            names_map[code] = best_name
            
        # Initialize nodes
        # We need a set of all bodies involved (centers and targets)
        all_ids = set()
        for segment in self.ephemeris.segments:
            all_ids.add(segment.center)
            all_ids.add(segment.target)
            
        for i in all_ids:
            hierarchy[i] = {
                'name': names_map.get(i, f"Body {i}"),
                'children': set()
            }
            
        # Build relationships
        # Note: Segments define state relative to a center.
        # This implies a hierarchy? Not strictly, but usually Center -> Target.
        # e.g. Earth Barycenter -> Moon
        for segment in self.ephemeris.segments:
            center = segment.center
            target = segment.target
            if center in hierarchy and target in hierarchy:
                hierarchy[center]['children'].add(target)
                
        # Convert sets to sorted lists for display
        for node in hierarchy.values():
            node['children'] = sorted(list(node['children']))
            
        return hierarchy, 0 # Return hierarchy and root ID (0 is typically SSB)
