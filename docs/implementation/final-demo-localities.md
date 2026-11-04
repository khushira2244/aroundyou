# Final demo-only locality placements

Reviewed 2026-11-02. Stable sourced locality centers are assigned to fictional scenarios only; they are not verified venues or claims that actual events occur there. Original fixture locations are retained in each publication snapshot under `demo_import.original_location`, and previous immutable publication revisions remain available. Real events and Canary Hill are excluded from the update. No offsets or random coordinates are generated.

Marker label: **Demo · Approximate location — venue unverified.**

| Event | Approximate locality | Latitude | Longitude | Locality reference |
| --- | --- | --- | --- | --- |
| Street Animal Feeding & Care Drive | Hurhuru | 23.97859 | 85.36893 | [Reference](https://mapcarta.com/35718856) |
| Weekend Learning Circle for Children | Matwari | 23.99606 | 85.38113 | [Reference](https://mapcarta.com/35718866) |
| Community Blood Donation Camp | Korra | 23.9929 | 85.38379 | [Reference](https://mapcarta.com/35718868) |
| Plant Native Trees Together | Jabra | 23.99605 | 85.38725 | [Reference](https://mapcarta.com/35718874) |
| Digital Literacy for Senior Citizens | Khirgaon | 23.98393 | 85.35399 | [Reference](https://mapcarta.com/35718852) |
| Winter Clothing Collection & Distribution | Haringanj | 23.98022 | 85.37703 | [Reference](https://mapcarta.com/35718870) |
| Community Lake & Pond Conservation | Katamdag | 23.9776 | 85.2907 | [Reference](https://mapcarta.com/37713100) |
| Accessible Neighborhood Initiative | Masratu | 23.98251 | 85.32383 | [Reference](https://mapcarta.com/35718836) |
| Women’s Skills & Livelihood Workshop | Lakhe | 23.98918 | 85.38888 | [Reference](https://mapcarta.com/35718876) |
| Community Heritage Preservation Walk | Kadma | 23.98736 | 85.34534 | [Reference](https://mapcarta.com/35718844) |

Verification: actual PostgreSQL/public API comparison found ten unique coordinate pairs, ten matching profile links, original location preservation and no Canary Hill import. Component test verifies ten markers use supplied coordinates without offsets and each click selects the correct event. Actual browser visual inspection remains pending; no visual pass is claimed.
