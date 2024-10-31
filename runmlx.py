# Script to run the logger

if __name__ == "__main__":
    import os
    if os.name != "nt":
        os.environ["GDK_BACKEND"] = "x11"

    import mlx.mlx
    mlx.mlx.main()
