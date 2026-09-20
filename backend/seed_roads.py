import uuid
from datetime import datetime, timezone

from app.database.session import SessionLocal
from app.api.routes.operations import Asset
from app.api.routes.roads import RoadSegment
from app.models.location import Location


def main():
    db = SessionLocal()

    try:
        locations = db.query(Location).all()

        if not locations:
            print("ERROR: No monitoring locations found.")
            print("Run your existing seed_data.py first.")
            return

        print(f"Found {len(locations)} monitoring locations.")

        # Create vulnerability assets from the first suitable locations.
        asset_specs = [
            ("Demo Village", "village", 2500, 0.75),
            ("Demo Hospital", "hospital", 500, 0.85),
            ("Demo School", "school", 800, 0.70),
            ("Demo Bridge", "bridge", 1200, 0.90),
            ("Demo Shelter", "shelter", 300, 0.60),
        ]

        assets = []

        for i, (name, kind, population, vulnerability) in enumerate(asset_specs):
            if i >= len(locations):
                break

            location = locations[i]

            # Do not duplicate assets if script is run again.
            existing = (
                db.query(Asset)
                .filter(Asset.data["name"].as_string() == name)
                .first()
            )

            if existing:
                asset = existing
                print(f"Asset already exists: {asset.id} - {name}")
            else:
                # Location model stores coordinates directly.
                latitude = getattr(location, "latitude", None)
                longitude = getattr(location, "longitude", None)

                # Fallback for JSON-backed location data.
                if latitude is None and hasattr(location, "data"):
                    latitude = location.data.get("latitude")

                if longitude is None and hasattr(location, "data"):
                    longitude = location.data.get("longitude")

                if latitude is None or longitude is None:
                    print(f"Skipping {name}: location has no coordinates.")
                    continue

                asset = Asset(
                    id=str(uuid.uuid4()),
                    data={
                        "name": name,
                        "location_id": location.location_id,
                        "kind": kind,
                        "latitude": latitude,
                        "longitude": longitude,
                        "population": population,
                        "vulnerability": vulnerability,
                        "access": "open",
                        "source": "Prototype demo data",
                    },
                )

                db.add(asset)
                db.flush()

                print(f"Created asset: {asset.id} - {name}")

            assets.append(asset)

        if len(assets) < 2:
            db.rollback()
            print("ERROR: Need at least 2 assets to create roads.")
            return

        # Use current UTC time so the road observations are fresh.
        observed_at = datetime.now(timezone.utc).isoformat()

        road_specs = [
            ("Demo Open Route", 0, 1, "open"),
            ("Demo Restricted Route", 1, 2, "restricted"),
            ("Demo Blocked Route", 2, 3, "blocked"),
            ("Demo Unknown Route", 3, 4, "unknown"),
        ]

        for name, a, b, status in road_specs:
            if a >= len(assets) or b >= len(assets):
                continue

            from_asset = assets[a]
            to_asset = assets[b]

            existing = (
                db.query(RoadSegment)
                .filter(RoadSegment.data["name"].as_string() == name)
                .first()
            )

            if existing:
                print(f"Road already exists: {name}")
                continue

            coordinates = [
                [
                    from_asset.data["longitude"],
                    from_asset.data["latitude"],
                ],
                [
                    to_asset.data["longitude"],
                    to_asset.data["latitude"],
                ],
            ]

            road = RoadSegment(
                id=str(uuid.uuid4()),
                data={
                    "name": name,
                    "from_asset": from_asset.id,
                    "to_asset": to_asset.id,
                    "status": status,
                    "source": "Prototype demo survey",
                    "observed_at": observed_at,
                    "coordinates": coordinates,
                },
            )

            db.add(road)
            print(f"Created road: {name} [{status}]")

        db.commit()

        print()
        print("========================================")
        print("ROAD CONNECTIVITY SEED COMPLETE")
        print("========================================")
        print(f"Assets: {len(assets)}")
        print("Road statuses: open, restricted, blocked, unknown")
        print()
        print("Now check:")
        print("http://127.0.0.1:8000/api/operations/assets")
        print("http://127.0.0.1:8000/api/operations/roads")

    except Exception as e:
        db.rollback()
        print("ERROR:", repr(e))
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
