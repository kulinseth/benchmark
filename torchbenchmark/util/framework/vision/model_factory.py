import torch
import torch.optim as optim
import torchvision.models as models
from torchbenchmark.util.model import BenchmarkModel

class TorchVisionModel(BenchmarkModel):
    optimized_for_inference = True
    # To recognize this is a torchvision model
    TORCHVISION_MODEL = True
    # These two variables should be defined by subclasses
    DEFAULT_TRAIN_BSIZE = None
    DEFAULT_EVAL_BSIZE = None

    def __init__(self, model_name, test, device, jit=False, batch_size=None, extra_args=[]):
        super().__init__(test=test, device=device, jit=jit, batch_size=batch_size, extra_args=extra_args)

        self.model = getattr(models, model_name)().to(self.device)
        self.example_inputs = (torch.randn((self.batch_size, 3, 224, 224)).to(self.device),)
        self.example_outputs = torch.rand_like(self.model(*self.example_inputs))
        if test == "train":
            self.model.train()
            # setup optimizer and loss_fn
            self.optimizer = optim.Adam(self.model.parameters())
            self.loss_fn = torch.nn.CrossEntropyLoss()
        elif test == "eval":
            self.model.eval()

        self.real_input = [ torch.rand_like(self.example_inputs[0]) ]
        self.real_output = [ torch.rand_like(self.example_outputs) ]

        if self.jit:
            if hasattr(torch.jit, '_script_pdt'):
                self.model = torch.jit._script_pdt(self.model, example_inputs=[self.example_inputs, ])
            else:
                self.model = torch.jit.script(self.model, example_inputs=[self.example_inputs, ])
            if test == "eval":
                # model needs to in `eval`
                # in order to be optimized for inference
                self.model = torch.jit.optimize_for_inference(self.model)

    def get_flops(self):
        return self.flops * self.batch_size

    def get_module(self):
        return self.model, self.example_inputs

    def train(self, niter=3):
        for _ in range(niter):
            self.optimizer.zero_grad()
            for data, target in zip(self.real_input, self.real_output):
                if self.extra_args.cudagraph:
                    self.example_inputs[0].copy_(data)
                    self.example_outputs.copy_(target)
                    self.g.replay()
                else:
                    pred = self.model(data)
                    self.loss_fn(pred, target).backward()
                    self.optimizer.step()

    def eval(self, niter=1):
        if self.extra_args.cudagraph:
            return NotImplementedError("CUDA Graph is not yet implemented for inference.")
        model = self.model
        example_inputs = self.example_inputs
        for _i in range(niter):
            model(*example_inputs)
