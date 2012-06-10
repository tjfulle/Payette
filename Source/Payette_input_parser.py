# The MIT License

# Copyright (c) 2011 Tim Fuller

# License for the specific language governing rights and limitations under
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
import os, sys


class InputError(Exception):
    def __init__(self, message):
        sys.tracebacklimit = 0
        from Source.Payette_utils import who_is_calling
        caller = who_is_calling()
        self.message = message + " [reported by {0}]".format(caller)
        super(InputError, self).__init__(self.message)


class InputParser(object):

    def __init__(self, user_input=None):

        self.errors = 0
        self.warnings = 0

        if user_input is None:
            sys.exit("no user input sent to InputParser")

        self.user_input = user_input

        # main container for holding all user input
        self.simkey = None
        self.input_set = []
        self.read_input()

        pass

    def report_error(self, msg):
        print "ERROR: {0}".format(msg)
        self.errors += 1

    def log_warning(self, msg):
        print "WARNING: {0}".format(msg)
        self.warnings += 1

    def read_input(self):
        """ read a list of user inputs and return """

        # get all of the input blocks for the file
        input_lines = self._get_input_lines(self.user_input)
        input_sets = self._get_blocks(input_lines)

        # input_sets contains a list of all blocks in the file, parse it to make
        # sure that a simulation is given
        recognized_blocks = ("simulation", "boundary", "legs", "material",
                             "optimization", "permutation", "enumeration",
                             "mathplot", "name", "content", "extraction",
                             "output")
        incompatible_blocks = (("visualization", "optimization", "enumeration"),)

        for input_set in input_sets:

            if "simulation" not in input_set:
                keys = ", ".join(input_set.keys())
                self.log_warning(
                    "expected to find a simulation block but found: {0}"
                    .format(keys))
                continue

            simkey = input_set["simulation"]["name"]
            if not simkey:
                self.report_error(
                    'did not find simulation name.  Simulation block '
                    'must be of form:\n'
                    '\tbegin simulation <simulation name> ... end simulation')
                continue

            # check for incompatibilities
            bad_blocks = [x for x in input_set["simulation"]
                          if x not in recognized_blocks]

            if bad_blocks:
                self.report_error(
                    "unrecognized blocks: {0}".format(", ".join(bad_blocks)))

            for item in incompatible_blocks:
                bad_blocks = [x for x in input_set["simulation"] if x in item]
                if len(bad_blocks) > 1:
                    self.report_error(
                        "{0} blocks incompatible, choose one"
                        .format(", ".join(bad_blocks)))
                continue

            self.simkey = simkey
            self.input_set = input_set["simulation"]

            continue

        if self.errors:
            raise InputError("stopping due to previous errors")

        return

    def _get_blocks(self, user_input):
        """ Find all input blocks in user_input.

        Input blocks are blocks of instructions in

            begin keyword [title]
                   .
                   .
                   .
            end keyword

        blocks.

        Parameters
        ----------
        user_input : array_like
            Split user_input

        Returns
        -------
        blocks : dict
            Dictionary containing all blocks.
            keys:
                simulation
                boundary
                legs
                special
                mathplot

        """

        block_tree = []
        block_stack = []
        block = {}

        for iline, line in enumerate(user_input):

            split_line = line.strip().lower().split()

            if not split_line:
                continue

            if split_line[0] == "begin":
                # Encountered a new block. Before continuing, we need to decide
                # what to do with it. Possibilities are:
                #
                #    1. Start a new block dictionary if this block is not nested
                #    2. Append this block to the previous if it is nested

                # get the block type
                try:
                    block_typ = split_line[1]

                except ValueError:
                    raise InputError(
                        "encountered a begin directive with no block type")

                # get the (optional) block name
                try:
                    block_nam = "_".join(split_line[2:])

                except ValueError:
                    block_nam = None

                new_block = {block_typ: {"name": block_nam, "content": [], }}

                if not block_stack:
                    # First encountered block, old block is now done, store it
                    if block:
                        block_tree.append(block)

                    block = new_block

                else:
                    if block_typ in block[block_stack[0]]:
                        raise InputError(
                            "duplicate block \"{0}\" encountered"
                            .format(block_typ))

                    block[block_stack[0]][block_typ] = new_block[block_typ]

                # Append the block type to the block stack. The block stack is a
                # list of blocks we are currently in.
                block_stack.append(block_typ)
                continue

            elif split_line[0] == "end":

                # Reached the end of a block. Make sure that it is the end of the
                # most current block.
                try:
                    block_typ = split_line[1]
                except ValueError:
                    raise InputError(
                        "encountered a end directive with no block type")

                if block_stack[-1] != block_typ:
                    msg = ('unexpected "end {0}" directive, expected "end {1}"'
                           .format(block_typ, block_stack[-1]))
                    raise InputError(msg)

                # Remove this block from the block stack
                block_stack.pop()
                try:
                    block_typ = block_stack[-1]

                except IndexError:
                    block_typ = None

                continue

            # Currently in a block,
            if not block_stack:
                continue

            if block_stack[0] == block_typ:
                block[block_typ]["content"].append(line)

            else:
                block[block_stack[0]][block_typ]["content"].append(line)

            continue

        block_tree.append(block)

        return block_tree

    def _remove_block(self, input_lines, block):
        """ remove the requested block from input_lines """
        idx_0, idx_f, lines = self._find_block(input_lines, block)
        del input_lines[idx_0:idx_f + 1]
        return input_lines

    def _find_block(self, input_lines, block):
        """ find block in input_lines """
        block_lines = []
        idx_0, idx_f = None, None
        for idx, line in enumerate(input_lines):
            sline = line.split()
            if sline[0].lower() == "begin":
                if sline[1] == block:
                    idx_0 = idx
            elif sline[0].lower() == "end":
                if sline[1] == block:
                    idx_f = idx
            continue

        if idx_0 is not None and idx_f is not None:
            block_lines = input_lines[idx_0 + 1:idx_f]

        return idx_0, idx_f, block_lines

    def _get_input_lines(self, raw_user_input):
        """Read the user input, inserting files if encountered

        Parameters
        ----------
        user_input : list
            New line separated list of the input file
        cchars : list
            List of comment characters

        Returns
        -------
        all_input : list
            All of the read input, including inserted files

        """

        insert_kws = ("insert", "include")

        cchars = ("#", "$")
        used_blocks = []
        all_input = []
        iline = 0

        user_input = _remove_all_comments(raw_user_input, cchars)

        # infinite loop for reading the input file and getting all inserted files
        while True:

            # if we have gone through one time, reset user_input to be all_input
            # and run through again until all inserted files have been read in
            if iline == len(user_input):
                if [x for x in all_input if x.split()[0] in insert_kws]:
                    user_input = [x for x in all_input]
                    all_input = []
                    iline = 0
                else:
                    break

            # get the next line of input
            line = user_input[iline]

            # check for internal "use" directives
            if line.split()[0] == "use":
                block = " ".join(line.split()[1:])
                # check if insert is given in file
                idx_0, idx_f, block_insert = self._find_block(user_input, block)
                if idx_0 is None:
                    raise InputError(
                        "'use' block '{0:s}' not found".format(block))
                elif idx_f is None:
                    raise InputError(
                        "end of 'use' block '{0:s}' not found".format(block))

                used_blocks.append(block)
                all_input.extend(block_insert)

            # check for inserts
            elif line.split()[0] in insert_kws:
                insert = " ".join(line.split()[1:])

                if not os.path.isfile(insert):
                    raise InputError(
                        "inserted file '{0:s}' not found".format(insert))

                insert_lines = open(insert, "r").readlines()
                all_input.extend(_remove_all_comments(insert_lines, cchars))

            else:
                all_input.append(line)

            iline += 1

            continue

        for block in list(set(used_blocks)):
            all_input = self._remove_block(all_input, block)

        return all_input

    def get_input_set(self):
        return self.input_set

    def get_simulation_key(self):
        return self.simkey

    def input_blocks(self):
        return self.input_set.keys()

    def get_block(self, block_name):
        block = self.input_set.get(block_name)
        if block is None:
            for input_block in self.input_blocks():
                if input_block.lower() == block_name.lower():
                    block = self.input_set[block]
                continue
            else:
                return None
        return block["content"]

    def set_block(self, block_name, content):
        self.input_set[block_name]["content"] = content
        return

    def remove_block(self, block_name):
        del self.input_set[block_name]
        return

    def has_block(self, block_name):
        return block_name in self.input_set

    def get_input_lines(self, skip=None):

        if skip is None:
            skip = []
        elif not isinstance(skip, (list, tuple)):
            skip = [skip]

        req_blocks = ("material", "boundary", "legs")
        inp_dict = self.input_set
        input_lines = []

        # simulation block
        input_lines.append("begin simulation {0}".format(self.simkey))
        content = self.input_set["content"]
        for item in content:
            input_lines.append(item)
            continue

        # required blocks
        for block in req_blocks:
            content = self.input_set[block]["content"]
            name = self.input_set[block]["name"]
            input_lines.append("begin {0} {1}".format(block, name))
            for item in content:
                input_lines.append(item)
                continue
            if block == "boundary":
                continue
            input_lines.append("end {0}".format(block))
            if block == "legs":
                input_lines.append("end boundary")
            continue

        for key, val in self.input_set.items():
            if not isinstance(val, dict) or key in skip:
                continue

            name = val["name"]
            content = val["content"]
            if key in req_blocks:
                continue
            input_lines.append("begin {0} {1}".format(key, name))
            for item in content:
                input_lines.append(item)
                continue
            input_lines.append("end {0}".format(key))
            input_lines.append("end simulation")

        return input_lines

    def input_options(self):
        return self.input_set["content"]


def parse_user_input(raw_user_input, user_cchar=None):
    """unfinish docstring """
    cchars = ['#','$']
    # comment characters
    if user_cchar is not None:
        cchars.append(user_cchar)

    user_input = _remove_all_comments(raw_user_input, cchars)

    use_blocks = []
    all_inputs = []
    current_input = []
    in_simulation = False
    for line in user_input:
        line = " ".join(line.strip().split())
        if "begin simulation" in line.lower():
            if current_input:
                sys.exit(
                    "beginning simulation encountered before end of previous")
            else:
                in_simulation = True

        if in_simulation:
            current_input.append(line)
        else:
            use_blocks.append(line)

        if "end simulation" in line.lower():
            all_inputs.append(current_input)
            current_input = []
            in_simulation = False
            continue

        continue

    # check for the end of each simulation and insert 'use' blocks
    for idx, item in enumerate(all_inputs):
        if "end simulation" not in item[-1]:
            sys.exit("end of simulation '{0}' not found".format(item[0]))

        item.extend(use_blocks)
        all_inputs[idx] = item
        continue

    return all_inputs


def _remove_all_comments(lines, cchars):
    """ remove all comments from lines """
    stripped_lines = []
    for line in lines:
        line = line.strip()
        # skip blank and comment lines
        if not line.split() or line[0] in cchars:
            continue

        # remove inline comments
        for cchar in cchars:
            line = line.split(cchar)[0]

        stripped_lines.append(line)
        continue
    return stripped_lines


def remove_block(lines, block_name):
    for iline, line in enumerate(lines):
        line = " ".join(line.strip().lower().split())
        if "begin {0}".format(block_name.lower()) in line:
            idx_0 = iline
        elif "end {0}".format(block_name.lower()) in line:
            idx_f = iline + 1
        continue
    return lines[:idx_0] + lines[idx_f:]


def replace_params_and_name(lines, name, param_names, param_vals):
    """Repace the values of parameter names in lines with those in param_vals

    """
    if not isinstance(param_names, (list, tuple)):
        param_names = [param_names]
    if not isinstance(param_vals, (list, tuple)):
        param_vals = [param_vals]
    if len(param_names) != len(param_vals):
        raise InputError("len(param_names) != len(param_vals)")

    nreplaced = 0
    job_inp = []
    for line in lines:
        line = " ".join(line.strip().split())
        if "begin simulation" in line:
            line = "begin simulation {0}".format(name)
            job_inp.append(line)
            continue

        key = line.split()[0]
        for idx, param in enumerate(param_names):
            if param.lower() == key.lower():
                line = ("{0} = {1}".format(param_names[idx], param_vals[idx]))
                nreplaced += 1
            continue

        job_inp.append(line)
        continue
    if nreplaced != len(param_names):
        raise InputError("could not replace all requested params")

    return job_inp