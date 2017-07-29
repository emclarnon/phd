import os.path
import sys
from decimal import Decimal


LIST_TYPES = {'TYPE:QCADLayer', 'TYPE:QCADCell', 'TYPE:CELL_DOT'}


def import_file(filename):
    with open(filename, 'r') as f:
        contents = {'header': 'file'}
        stack = []
        current = contents
        header = ''
        for line in f:
            line = line.strip()
            if line.startswith('['):
                if line.startswith('[#'):
                    closed = current
                    current = stack.pop()
                    if header in LIST_TYPES:
                        if header in current.keys():
                            current[header].append(closed)
                        else:
                            current[header] = [closed]
                    else:
                        if header in current.keys():
                            raise Exception("Unexpected header: {}".format(header))
                        else:
                            current[header] = closed
                    header = current['header']
                else:
                    header = line[1:-1]
                    stack.append(current)
                    current = {}
                    current['header'] = header
            else:
                k, v = line.split('=')
                current[k] = v

    return current


def convert_dots(dots):
    output = []
    for dot in dots:
        output.append('[QDOT]')

        # Populate Dot properties
        output.append('x=%.6E' % Decimal(dot['x']))
        output.append('y=%.6E' % Decimal(dot['y']))
        output.append('diameter=%.6E' % Decimal(dot['diameter']))
        output.append('charge={}'.format(dot['charge']))
        output.append('spin=%.6E' % Decimal(dot['spin']))
        output.append('potential=%.6E' % Decimal(dot['potential']))

        output.append('[#QDOT]')

    return output


def convert_cells(cells):
    output = []
    for cell in cells:
        output.append('[QCELL]')

        # Populate Cell properties
        props = cell['TYPE:QCADDesignObject']
        output.append('x=%.6E' % Decimal(props['x']))
        output.append('y=%.6E' % Decimal(props['y']))

        top_x = float(props['bounding_box.xWorld'])
        top_y = float(props['bounding_box.yWorld'])
        bot_x = top_x + float(props['bounding_box.cxWorld'])
        bot_y = top_y + float(props['bounding_box.cyWorld'])
        output.append('top_x=%.6E' % Decimal(str(top_x)))
        output.append('top_y=%.6E' % Decimal(str(top_y)))
        output.append('bot_x=%.6E' % Decimal(str(bot_x)))
        output.append('bot_y=%.6E' % Decimal(str(bot_y)))

        output.append('cell_width=%.6E' % Decimal(cell['cell_options.cxCell']))
        output.append('cell_height=%.6E' % Decimal(cell['cell_options.cyCell']))

        output.append('orientation=0')

        r = props['clr.red']
        g = props['clr.green']
        b = props['clr.blue']
        if r == '0' and g == '65535' and b == '0':  # Green
            color = '0'
        elif r == '0' and g == '0' and b == '65535':  # Blue
            color = '2'
        elif r == '65535' and g == '65535' and b == '0':  # Yellow
            color = '3'
        elif r == '65535' and g == '0' and b == '65535':  # Pink
            color = '5'
        elif r == '0' and g == '65535' and b == '65535':  # Cyan
            color = '6'
        elif r == '65535' and g == '65535' and b == '65535':  # White
            color = '7'
        else:
            raise Exception('Unknown color: {},{},{}'.format(r, g, b))
        output.append('color={}'.format(color))

        output.append('clock={}'.format(cell['cell_options.clock']))

        is_input = '0'
        is_output = '0'
        is_fixed = '0'
        func = cell['cell_function']
        if func == 'QCAD_CELL_INPUT':
            is_input = '1'
        elif func == 'QCAD_CELL_OUTPUT':
            is_output = '1'
        output.append('is_input={}'.format(is_input))
        output.append('is_output={}'.format(is_output))
        output.append('is_fixed={}'.format(is_fixed))

        label = 'NO NAME'
        if 'TYPE:QCADLabel' in cell.keys():
            label = cell['TYPE:QCADLabel']['psz']
        output.append('label={}'.format(label))

        dots = cell['TYPE:CELL_DOT']
        output.append('number_of_dots={}'.format(len(dots)))
        output = output + convert_dots(dots)

        output.append('[#QCELL]')

    return output


def convert_file(content):
    ver = content['VERSION']['qcadesigner_version']
    if ver != '2.000000':
        print 'Invalid file version: {}'.format(ver)

        return

    output = []

    # Write file header
    output.append('[VERSION]')
    output.append('qcadesigner_version=1.400000')
    output.append('[#VERSION]')
    output.append('[DESIGN_OPTIONS]')
    output.append('grid_spacing=1.000000e+001')
    output.append('[#DESIGN_OPTIONS]')
    output.append('[DESIGN_PROPERTIES]')
    output.append('total_number_of_cells=')
    output.append('[#DESIGN_PROPERTIES]')

    content = content['TYPE:DESIGN']

    for layer in content['TYPE:QCADLayer']:
        if layer['type'] == '1':
            cells = layer['TYPE:QCADCell']
            output[7] = output[7] + str(len(cells))
            output = output + convert_cells(cells)

    return output


def write_file(filename, content):
    filename = '{}.141'.format(filename)
    print 'Writing {}...'.format(filename)
    with open(filename, 'w') as f:
        for line in content:
            f.write('{}\n'.format(line))


def process_files(args):
    for arg in args:
        print 'Processing {}...'.format(arg)
        if not os.path.isfile(arg):
            print 'File {} does not exist. Skipping...'.format(arg)
            continue

        content = import_file(arg)
        content = convert_file(content)

        if content is not None:
            write_file(arg, content)


if __name__ == '__main__':
    process_files(sys.argv[1:])
