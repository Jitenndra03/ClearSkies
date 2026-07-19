INTERVENTIONS = {
    "construction": [
        "Deploy water sprinklers at {ward} construction sites before 6 AM",
        "Issue dust suppression notice to contractors in {ward}",
        "Mandate tarpaulin covering for all material storage in {ward}"
    ],
    "industrial": [
        "Issue stack emission compliance notice to industries in {ward}",
        "Schedule unannounced inspection of industrial units in {ward}",
        "Coordinate with SPCB for emission source audit in {ward}"
    ],
    "vehicular": [
        "Deploy traffic marshals to decongest {ward} arterial roads",
        "Enforce PUC check camps on entry points to {ward}",
        "Activate odd-even restriction on {ward} corridor today"
    ],
    "agricultural": [
        "Issue stubble burning prohibition notice for {ward} periphery",
        "Deploy field officers to monitor crop residue burning near {ward}",
        "Coordinate with agriculture dept for {ward} biomass collection"
    ],
    "dust": [
        "Deploy road sweeping machines on {ward} main roads",
        "Schedule water tanker sprinkling on {ward} unpaved stretches",
        "Issue road dust suppression advisory for {ward} municipality"
    ]
}

class RecommendationAgent:
    def generate(self, hotspots: list) -> list:
        queue = []
        for i, hotspot in enumerate(hotspots):
            source = hotspot.get("source", "dust")
            ward = hotspot.get("ward", "Unknown")
            
            actions = INTERVENTIONS.get(source, INTERVENTIONS["dust"])
            action_template = actions[i % len(actions)]
            action = action_template.format(ward=ward)
            
            aqi = hotspot.get("aqi", 0)
            confidence = hotspot.get("confidence", 0.0)
            priority_score = round((aqi / 500) * confidence, 2)
            
            queue_item = {
                "id": hotspot.get("id", f"enf-{i:03d}"),
                "ward": ward,
                "source": source,
                "action": action,
                "priority_score": priority_score,
                "status": "Pending",
                "before_aqi": aqi,
                "after_aqi": None
            }
            queue.append(queue_item)
            
        queue.sort(key=lambda x: x["priority_score"], reverse=True)
        return queue
