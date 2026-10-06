import geopandas as gpd
import pandas as pd

STD_RESULT = "results/full/std/default.geojson"
STD_330300_RESULT = "results/full/std_330300/default.geojson"


def main():
    std = gpd.read_file(STD_RESULT)
    std_330300 = gpd.read_file(STD_330300_RESULT)

    ids_std = set(std["id"])
    ids_330300 = set(std_330300["id"])

    common = ids_std & ids_330300
    only_std = ids_std - ids_330300
    only_330300 = ids_330300 - ids_std
    union = ids_std | ids_330300

    jaccard = len(common) / len(union) if union else 1.0

    print("STD vs STD_330300")
    print("=" * 60)
    print(f"Celle STD:                 {len(ids_std)}")
    print(f"Celle STD_330300:          {len(ids_330300)}")
    print(f"Celle comuni:              {len(common)}")
    print(f"Celle che escono da STD:   {len(only_std)}")
    print(f"Celle che entrano:         {len(only_330300)}")
    print(f"Jaccard:                    {jaccard:.4f}")

    print("\nEscono:")
    print(sorted(only_std))

    print("\nEntrano:")
    print(sorted(only_330300))

    diagnostic_columns = [
        "benefit_3",
        "benefit_30",
        "benefit_300",
        "benefit_330300",
        "base_benefit",
        "contribution_330300",
    ]

    available = [
        column for column in diagnostic_columns
        if column in std_330300.columns
    ]

    if available:
        print("\nDiagnostica STD_330300 sulle celle selezionate")
        print("=" * 60)

        summary = pd.DataFrame({
            "mean": std_330300[available].mean(),
            "min": std_330300[available].min(),
            "max": std_330300[available].max(),
        })

        print(summary.round(6).to_string())


if __name__ == "__main__":
    main()