import argparse
from typing import List
from torchbenchmark.util.backends.fx2trt import enable_fx2trt
from torchbenchmark.util.backends.fuser import enable_fuser
from torchbenchmark.util.backends.torch_trt import enable_torchtrt
from torchbenchmark.util.backends.flops import enable_flops
from torchbenchmark.util.framework.vision.args import enable_fp16

def add_bool_arg(parser: argparse.ArgumentParser, name: str, default_value: bool=True):
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('--' + name, dest=name, action='store_true')
    group.add_argument('--no-' + name, dest=name, action='store_false')
    parser.set_defaults(**{name: default_value})

def is_torchvision_model(model: 'torchbenchmark.util.model.BenchmarkModel') -> bool:
    return hasattr(model, 'TORCHVISION_MODEL') and model.TORCHVISION_MODEL

def allow_fp16(model: 'torchbenchmark.util.model.BenchmarkModel') -> bool:
    return is_torchvision_model(model) and model.test == 'eval' and model.device == 'cuda'


# Dispatch arguments based on model type
def parse_args(model: 'torchbenchmark.util.model.BenchmarkModel', extra_args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--flops", action='store_true', help="enable flops counting")
    parser.add_argument("--fx2trt", action='store_true', help="enable fx2trt")
    parser.add_argument("--fuser", type=str, default="", help="enable fuser")
    parser.add_argument("--torch_trt", action='store_true', help="enable torch_tensorrt")
    # TODO: Enable fp16 for all model inference tests
    # fp16 is only True for torchvision models running CUDA inference tests
    # otherwise, it is False
    fp16_default_value = False
    if allow_fp16(model):
        fp16_default_value = True
    add_bool_arg(parser, "fp16", fp16_default_value)
    args = parser.parse_args(extra_args)
    args.device = model.device
    args.jit = model.jit
    args.test = model.test
    args.batch_size = model.batch_size
    if args.device == "cpu":
        args.fuser = None
    if not allow_fp16(model) and args.fp16:
        raise NotImplementedError("fp16 is only implemented for torchvision models inference tests on CUDA.")
    if not (model.device == "cuda" and model.test == "eval"):
        if args.fx2trt or args.torch_trt:
            raise NotImplementedError("TensorRT only works for CUDA inference tests.")
    if hasattr(model, 'TORCHVISION_MODEL') and model.TORCHVISION_MODEL:
        args.cudagraph = False
    elif args.flops:
        args.flops = False
        raise NotImplementedError("Flops is only enabled for TorchVision models")
    return args

def apply_args(model: 'torchbenchmark.util.model.BenchmarkModel', args: argparse.Namespace):
    if args.fuser:
        enable_fuser(args.fuser)
    if args.fp16:
        assert allow_fp16(model), "Eval fp16 is only available on CUDA for torchvison models."
        model.model, model.example_inputs = enable_fp16(model.model, model.example_inputs)
    if args.fx2trt:
        if args.jit:
            raise NotImplementedError("fx2trt with JIT is not available.")
        module, exmaple_inputs = model.get_module()
        model.set_module(enable_fx2trt(args.batch_size, fp16=args.fp16, model=module, example_inputs=exmaple_inputs))
    if args.torch_trt:
        module, exmaple_inputs = model.get_module()
<<<<<<< HEAD
        precision = 'fp16' if args.fp16 else 'fp32'
        model.set_module(enable_torchtrt(precision=precision, model=module, example_inputs=exmaple_inputs))

=======
        model.set_module(enable_torchtrt(precision='fp32', model=module, example_inputs=exmaple_inputs))
    if args.flops:
        enable_flops(model)
>>>>>>> f87426f9 (Fixed flops counting for torchvision.)
