#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shadow Hunt v3.0 - Library Test"""

import os
import sys

os.environ["OLLAMA_HOST"] = "http://localhost:11434"

def test_all():
    print("=" * 60)
    print("  Shadow Hunt v3.0 - Library Test")
    print("=" * 60)
    
    results = []
    
    # 1. PyTorch
    print("\n[1/10] PyTorch...")
    try:
        import torch
        print(f"  [OK] PyTorch: {torch.__version__}")
        results.append(("PyTorch", True))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("PyTorch", False))
    
    # 2. OpenCV
    print("\n[2/10] OpenCV...")
    try:
        import cv2
        print(f"  [OK] OpenCV: {cv2.__version__}")
        results.append(("OpenCV", True))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("OpenCV", False))
    
    # 3. Ultralytics
    print("\n[3/10] Ultralytics (YOLO)...")
    try:
        from ultralytics import YOLO
        import ultralytics
        print(f"  [OK] Ultralytics: {ultralytics.__version__}")
        results.append(("Ultralytics", True))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("Ultralytics", False))
    
    # 4. DeepSORT
    print("\n[4/10] DeepSORT...")
    try:
        from deep_sort_realtime.deepsort_tracker import DeepSort
        tracker = DeepSort()
        print(f"  [OK] DeepSORT: Ready")
        results.append(("DeepSORT", True))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("DeepSORT", False))
    
    # 5. Supervision
    print("\n[5/10] Supervision...")
    try:
        import supervision as sv
        print(f"  [OK] Supervision: {sv.__version__}")
        results.append(("Supervision", True))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("Supervision", False))
    
    # 6. PyAV
    print("\n[6/10] PyAV...")
    try:
        import av
        print(f"  [OK] PyAV: {av.__version__}")
        results.append(("PyAV", True))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("PyAV", False))
    
    # 7. FAISS
    print("\n[7/10] FAISS...")
    try:
        import faiss
        print(f"  [OK] FAISS: {faiss.__version__}")
        results.append(("FAISS", True))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("FAISS", False))
    
    # 8. Grounding DINO
    print("\n[8/10] Grounding DINO...")
    try:
        from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection
        print(f"  [OK] Grounding DINO: Available")
        results.append(("Grounding DINO", True))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("Grounding DINO", False))
    
    # 9. Ollama
    print("\n[9/10] Ollama...")
    try:
        import ollama
        models = ollama.list()
        print(f"  [OK] Ollama: Connected ({len(models['models'])} models)")
        results.append(("Ollama", True))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("Ollama", False))
    
    # 10. FastAPI
    print("\n[10/10] FastAPI...")
    try:
        from fastapi import FastAPI
        import fastapi
        print(f"  [OK] FastAPI: {fastapi.__version__}")
        results.append(("FastAPI", True))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("FastAPI", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "[OK]" if result else "[FAIL]"
        print(f"  {status} {name}")
    
    print("=" * 60)
    print(f"  PASSED: {passed}/{total}")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(test_all())