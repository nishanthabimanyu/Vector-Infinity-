import h5py
from skyfield.api import load
from datetime import datetime, timedelta

print("="*70)
print("DATA COVERAGE COMPARISON: DE441.BSP vs SOLAR_SYSTEM.H5")
print("="*70)

# === HDF5 Coverage ===
print("\n📦 HDF5 CACHE (solar_system.h5):")
with h5py.File('solar_system.h5', 'r') as f:
    time_jd = f['time_jd'][:]
    jd_start = time_jd[0]
    jd_end = time_jd[-1]
    total_points = len(time_jd)
    
    # Convert JD to calendar dates (approximate)
    # JD 0 = 4713 BC, JD 2400000 = 1858 AD
    years_span = (jd_end - jd_start) / 365.25
    days_span = jd_end - jd_start
    
    print(f"   Time Points: {total_points:,}")
    print(f"   JD Range: {jd_start:.2f} to {jd_end:.2f}")
    print(f"   Days Span: {days_span:,.0f} days")
    print(f"   Years Span: {years_span:,.1f} years")
    
    # Estimate calendar dates
    # Rough conversion: JD 2451545.0 = Jan 1, 2000 12:00 TT
    j2000_offset = 2451545.0
    start_offset = (jd_start - j2000_offset) / 365.25
    end_offset = (jd_end - j2000_offset) / 365.25
    
    print(f"\n   Approximate Calendar Range:")
    print(f"   Start: ~{2000 + start_offset:.0f}")
    print(f"   End:   ~{2000 + end_offset:.0f}")

# === BSP Coverage ===
print("\n🌌 BSP EPHEMERIS (de441.bsp):")
try:
    eph = load('de441.bsp')
    
    # Get Earth as representative body
    earth = eph['earth']
    
    # Access the SPK segment metadata
    # This is SPICE-specific and requires low-level access
    # Skyfield abstracts this, but we can check the file directly
    import jplephem
    from jplephem.spk import SPK
    
    spk = SPK.open('de441.bsp')
    
    # Get segments
    segments = list(spk.segments)
    
    if segments:
        # Find min/max across all segments
        earliest_start = min(seg.start_jd for seg in segments)
        latest_end = max(seg.end_jd for seg in segments)
        
        bsp_days_span = latest_end - earliest_start
        bsp_years_span = bsp_days_span / 365.25
        
        print(f"   Total Segments: {len(segments)}")
        print(f"   JD Range: {earliest_start:.2f} to {latest_end:.2f}")
        print(f"   Days Span: {bsp_days_span:,.0f} days")
        print(f"   Years Span: {bsp_years_span:,.1f} years")
        
        # Approximate calendar dates
        start_offset_bsp = (earliest_start - j2000_offset) / 365.25
        end_offset_bsp = (latest_end - j2000_offset) / 365.25
        
        print(f"\n   Approximate Calendar Range:")
        print(f"   Start: ~{2000 + start_offset_bsp:.0f}")
        print(f"   End:   ~{2000 + end_offset_bsp:.0f}")
        
        # Sample segment details
        print(f"\n   Sample Segment (Earth):")
        for seg in segments[:3]:
            if 'EARTH' in seg.describe().upper() or seg.target == 399:
                print(f"   - Target: {seg.target}, Center: {seg.center}")
                print(f"     Range: JD {seg.start_jd:.2f} to {seg.end_jd:.2f}")
                break
    
    spk.close()
    
except Exception as e:
    print(f"   Error reading BSP: {e}")

# === Comparison ===
print("\n" + "="*70)
print("VERDICT:")
print("="*70)

if 'days_span' in locals() and 'bsp_days_span' in locals():
    print(f"\n✓ HDF5:  {days_span:,.0f} days ({years_span:,.1f} years)")
    print(f"✓ BSP:   {bsp_days_span:,.0f} days ({bsp_years_span:,.1f} years)")
    
    if days_span >= 30000:
        print(f"\n🎯 HDF5 has {days_span/30000:.1f}x the '30,000 days' you asked for!")
    else:
        print(f"\n⚠️ HDF5 has {days_span:,.0f} days (needs {30000-days_span:,.0f} more for 30k)")
    
    if bsp_days_span >= 30000:
        print(f"🎯 BSP has {bsp_days_span/30000:.1f}x the '30,000 days' you asked for!")
    else:
        print(f"⚠️ BSP has {bsp_days_span:,.0f} days (needs {30000-bsp_days_span:,.0f} more for 30k)")
