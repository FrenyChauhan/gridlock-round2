# MongoDB Atlas Migration Guide

## Why Migrate
Current CSV-based system works for prototype (247k rows in memory ~180MB).
As ASTRaM feed grows (estimated +50k rows/month), migrate to MongoDB Atlas.

## Migration Path

### Phase 1 (Current — Prototype)
CSV files → pandas in-memory → FastAPI routers

### Phase 2 (3-6 months, ~500k rows)
MongoDB Atlas Free Tier → same router interface
Only database.py changes, routers unchanged.

### Phase 3 (Production, 1M+ rows)
MongoDB Atlas M10+ with:
- Geospatial indexes on (latitude, longitude)
- Compound index on (cluster_id, time_band, week)
- TTL index for old outcomes (keep 2 years)
- Change streams for real-time ASTRaM feed

## Collections Schema

violations:
  _id, id, latitude, longitude, cluster_id, time_band,
  vehicle_type, vehicle_weight, offence_code, 
  primary_violation, primary_violation_severity,
  created_date (indexed), police_station, 
  sample_weight, week (indexed)

clusters:
  _id, cluster_id, centroid_lat, centroid_lon,
  radius, dominant_station, cluster_size,
  tier, priority_score, cii_score,
  volatility_class, trend_slope,
  assigned_team_id, assignment_status

teams:
  _id, team_id, status, station, category,
  current_zone_id, expected_free_at

assignments:
  _id, assignment_id, team_id, zone_id,
  status, assigned_at, arrived_at, resolved_at

outcomes:
  _id, outcome_id, assignment_id, cluster_id,
  predicted_violations, actual_violations_found,
  outcome_type, response_time_minutes,
  created_at (TTL indexed, expire after 730 days)

## Geospatial Query Example
db.violations.createIndex({location: "2dsphere"})
db.violations.find({
  location: {
    $near: {
      $geometry: {type: "Point", coordinates: [77.5946, 12.9716]},
      $maxDistance: 2000
    }
  }
})
