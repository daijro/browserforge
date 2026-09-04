from browserforge.headers import HeaderGenerator


def main():
    for k, v in HeaderGenerator().generate().items():
        print(f"{k}: {v}")

if __name__ == "__main__":
    main()
