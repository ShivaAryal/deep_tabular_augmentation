import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import nn
from torch.autograd import Variable


class customLoss(nn.Module):
    def __init__(self):
        super(customLoss, self).__init__()
        self.mse_loss = nn.MSELoss(reduction="sum")
    
    def forward(self, x_recon, x, mu, logvar):
        loss_MSE = self.mse_loss(x_recon, x)
        loss_KLD = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
        return loss_MSE + loss_KLD


def lin_layer(ni, no):
    return nn.Sequential(
        nn.Linear(ni, no), nn.BatchNorm1d(no), nn.ReLU())


def get_lin_layers(input_shape, output_shapes:list):
    output_shapes = [input_shape] + output_shapes
    return [
        lin_layer(output_shapes[i], output_shapes[i+1])
        for i in range(len(output_shapes)-1)
    ]

def get_lin_layers_rev(input_shape, output_shapes:list):
    output_shapes =  output_shapes[::-1] + [input_shape]
    layers= [
        lin_layer(output_shapes[i], output_shapes[i+1])
        for i in range(len(output_shapes)-1)
    ]
    # we do not want the last layer to be put through a ReLU
    layers[-1] = layers[-1][:-1]
    return layers
    


class Autoencoder(nn.Module):
    def __init__(self,lin_layers,lin_layers_rev,latent_dim=3):
       
        #Encoder
        super(Autoencoder,self).__init__()
        self.encoder = lin_layers
        
        # Latent vectors mu and sigma
        self.fc1 = nn.Linear(lin_layers[-1][0].out_features, latent_dim)
        self.bn1 = nn.BatchNorm1d(num_features=latent_dim)
        self.fc21 = nn.Linear(latent_dim, latent_dim)
        self.fc22 = nn.Linear(latent_dim, latent_dim)

        # Sampling vector
        self.fc3 = nn.Linear(latent_dim, latent_dim)
        self.fc_bn3 = nn.BatchNorm1d(latent_dim)
        self.fc4 = nn.Linear(latent_dim, lin_layers[-1][0].out_features)
        self.fc_bn4 = nn.BatchNorm1d(lin_layers[-1][0].out_features)
        
        # Decoder
        self.decoder = lin_layers_rev
        
    def encode(self, x):

        fc1 = F.relu(self.bn1(self.fc1(self.encoder(x))))
        r1 = self.fc21(fc1)
        r2 = self.fc22(fc1)
        
        return r1, r2
    
    def reparameterize(self, mu, logvar):
        if self.training:
            std = logvar.mul(0.5).exp_()
            eps = Variable(std.data.new(std.size()).normal_())
            return eps.mul(std).add_(mu)
        else:
            return mu
        
    def decode(self, z):
        fc3 = F.relu(self.fc_bn3(self.fc3(z)))
        fc4 = F.relu(self.fc_bn4(self.fc4(fc3)))

        return self.decoder(fc4)
        
    def forward(self, x):
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        return self.decode(z), mu, logvar
