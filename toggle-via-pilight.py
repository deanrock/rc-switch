import sys
import requests


if __name__ == '__main__':
    x = sys.argv[1]

    cmd = ['pilight-send', '-p', 'raw', '-c']
    raw=[]

    mapping={
        '1': 900,
        '0': 230,
        'e': 8700
    }

    for i in x:
        raw.append(str(mapping[i]))

    cmd.append(' '.join(raw))

    print(' '.join(raw))
    print(cmd)

    r = requests.get('http://localhost:5001/send', params={
        'protocol': 'raw',
        'code': ' '.join(raw)
    })


    print(r.text)
