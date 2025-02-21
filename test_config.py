from src.config import Config

def test_configuration():
    """Test the configuration loading"""
    config = Config()
    
    # Configuration has been validated and printed during Config initialization
    
    # Return success if we have at least one account
    return len(config.accounts) > 0

if __name__ == "__main__":
    success = test_configuration()
    if not success:
        print("\nConfiguration test failed!")
        exit(1)
    else:
        print("\nConfiguration test passed!")