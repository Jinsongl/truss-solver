#! /usr/bin/env python

'''
solves a truss defined by the files joints.in, members.in and supports.in
returns a file result.out with the resultant forces

step 1: read input files joints.in, members.in, supports.in, applied.in.
        begin constructing the relevant tables
step 2: expand the members table to include dx, dy, L, lij, mij
step 3: construct a 2nx2n matrix of coefficients C, where n = # joints
step 4: construct the "applied forces" vector P
step 5: solve the matrix equation C.Q=P, where Q is a list of unknowns
step 6: find the maximum load
step 7: draw the bridge and label C/T members
'''

import numpy as np

path = raw_input('input the numbered file in "/straw bridge" containing the .in files: ')
if path[-1] != '/':
    path = path + '/'
path = '/home/bennett/Documents/ensc1002/straw bridge/' + path

# ------ step 1 ------
print "reading input files.. "

with open(path+'joints.in','r') as fin:
    joints = np.genfromtxt(fin, comments="#", delimiter="\t")

with open(path+'members.in', 'r') as fin:
    members = np.genfromtxt(fin, comments="#", delimiter="\t")

with open(path+'supports.in', 'r') as fin:
    supports = np.genfromtxt(fin, comments="#")

with open(path+'applied.in','r') as fin:
    applied = np.genfromtxt(fin, comments="#", delimiter="\t")

material = {}
with open(path+'material.in', 'r') as fin:
    for line in fin:
        if (line[0] != '#'):
            spl = line.split()
            if len(spl)==2:
                (key, value) = spl 
                material[key] = float(value)


# ------ step 2 ------
print "constructing matrices.. "

zeroes = [[0]]*members.shape[0]
for n in range(5):
    members = np.concatenate((members, zeroes), 1)
# members table now has five extra columns (empty)

for k in range(members.shape[0]):
    i   = members[k,1]
    j   = members[k,2]
    # get the values
    dx  = joints[j-1,1] - joints[i-1,1]
    dy  = joints[j-1,2] - joints[i-1,2]
    L   = np.sqrt(dx**2 + dy**2)
    lij = dx/L
    mij = dy/L
    # put them in the table
    members[k,3], members[k,4], members[k,5], members[k,6], members[k,7]\
        = dx, dy, L, lij, mij

# the members table is now fully populated with lij, mij


# ------ step 3: construct C ------
n = joints.shape[0] 
C = np.zeros((2*n,2*n))
for k in range(members.shape[0]):
    i   = members[k,1]
    j   = members[k,2]
    lij = members[k,6]
    mij = members[k,7]    
    C[2*i-2, k] = lij
    C[2*i-1, k] = mij
    C[2*j-2, k] = -lij
    C[2*j-1, k] = -mij

# now add the coefficients for the reaction forces:
C[2*supports[0]-2, 2*n-3] = 1
C[2*supports[1]-1, 2*n-2] = 1
C[2*supports[2]-1, 2*n-1] = 1
# C is complete!

'''
with open(path+'C.mat', 'w') as fout:
    np.savetxt(fout, C, fmt='%.3f', delimiter='\t')
'''


# ------ step 4: construct P ------
P = np.zeros(2*n)
num = applied.shape[0]-1
for i in range(1,num+1):
    P[2*applied[i,0]-2] = -applied[i,1]
    P[2*applied[i,0]-1] = -applied[i,2]


# ------ step 5: solve ------
print "solving.. "
fout = open(path+'result.out', 'w')

try:
    Q = np.linalg.solve(C,P)
except np.linalg.LinAlgError:
    print "singular matrix. using least squares.."
    fout.write("The truss produced a singular matrix. Used least-squares to solve...\n\n")
    Q = np.linalg.lstsq(C,P)[0]
    with open(path+'Q.mat','w') as fq:
        np.savetxt(fq, Q, fmt='%.3f', delimiter='\t')
    for i in range(len(Q)):
        if abs(Q[i]) < 0.001:
            Q[i] = 0.0

print "writing output.. "
names = ['R'+str(int(supports[0]))+'x',\
         'R'+str(int(supports[1]))+'y',\
         'R'+str(int(supports[2]))+'y']
coord = ['x', 'y', 'y']

def state(x):
    if (x<0):
        return 'comp.'
    elif (x>0):
        return 'tens.'
    else:
        return ''

# output a table of all members' internal forces
for i in range(members.shape[0]):
    fout.write(str(i+1) + '\t' + state(Q[i]) + '\t' + str(Q[i]) + '\n')
for i in range(3):
    fout.write('R' + str(int(supports[i])) + coord[i] + '\t' \
                   + '\t' \
                   + str(Q[members.shape[0]+i]) + '\n')
fout.write('\n')

# ------ step 6: find the maximum load ------
# find the members under the highest forces
intforces = Q.tolist()[:-3]
maxC   = min(intforces)
maxC_m = [i for i,j in enumerate(intforces) if j == maxC]
maxT   = max(intforces)
maxT_m = [i for i,j in enumerate(intforces) if j == maxT]

fout.write('\nmembers under most compression: \n')
for i in maxC_m:
    fout.write('member ' + str(i+1) + ':\t' + str(maxC) + '\n')
fout.write('\nmembers under most tension: \n')
for i in maxT_m:
    fout.write('member ' + str(i+1) + ':\t' + str(maxT) + '\n')

# use the material properties in materials.in to find the safe load
# first, buckling:
# just in case they are different lengths, use the max length of maxC
maxC_l = [0]*len(maxC_m)
for i in range(len(maxC_m)):
    maxC_l[i] = members[maxC_m[i],5] 
maxL_buckling = np.pi**2 * material['E'] * material['I'] \
                    / (abs(maxC) * max(maxC_l)**2) 

# second, yield:
maxF = max(maxT, abs(maxC))
maxL_yield = material['sf'] * material['s_y'] * material['A'] / maxF

maxL = min(maxL_yield, maxL_buckling)
fout.write('\nmax load:\t' + str(maxL) + ' N\n')
fout.write('\t\t' + str(maxL/9.81) + ' kg\n')
fout.close()


# ------ step 7: draw the bridge ------
# find the length of the truss and scale it accordingly

import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import matplotlib.text as text
fig = plt.figure()
ax = fig.add_subplot(1,1,1)

# find the unit length and scale accordingly
unit = 1000000
maxX = 0
for k in range(members.shape[0]):
    if members[k,5] < unit:
        unit = members[k,5]
for i in range(joints.shape[0]):
    joints[i,1], joints[i,2] = joints[i,1]/unit, joints[i,2]/unit
    if joints[i,1] > maxX:
        maxX = joints[i,1]

# draw the members first
for k in range(members.shape[0]):
    i, j = members[k,1], members[k,2]
    ix, iy, jx, jy = joints[i-1,1], joints[i-1,2], joints[j-1,1], joints[j-1,2]
    ix, iy, jx, jy = ix, iy, jx, jy
    c = "#ff0000" if Q[k]>0 else ("#0000ff" if Q[k]<0 else "#00ff00")
    ax.add_line(mlines.Line2D([ix,jx], [iy,jy], lw=2., color=c))
    mx = (ix+jx)/2
    my = (iy+jy)/2
    ax.text(mx,my,str(int(members[k,0])), fontsize=8)

for i in range(joints.shape[0]):
    ax.plot(joints[i,1], joints[i,2], 'ko')

ax.axis([-1,maxX+1,-maxX/2,maxX/2])
ax.axis('off')
fig.savefig(path + 'mpl.png')

print "analysis complete!"
