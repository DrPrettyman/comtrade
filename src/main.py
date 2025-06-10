import argparse
from create_viz import create_trade_visualization

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create trade visualization")
    parser.add_argument("commodity", help="Commodity to visualize (e.g., wine) or hscode (e.g. 2204)")
    parser.add_argument("year", type=int, help="Year to visualize")
    
    args = parser.parse_args()
    create_trade_visualization(args.commodity, args.year)