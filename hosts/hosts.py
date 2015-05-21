# -*- coding: utf-8 -*-
""" This module contains the classes required to manage a hosts file """
import sys
import exception
from utils import is_ipv4, is_ipv6, valid_hostnames


class HostsEntry(object):
    """ An entry in a hosts file. """
    def __init__(self, entry_type=None, address=None, comment=None, names=None):
        if not entry_type or entry_type not in ('ipv4',
                                                'ipv6',
                                                'comment',
                                                'blank'):
            raise Exception('entry_type invalid or not specified')

        if entry_type == 'comment' and not comment:
            raise Exception('entry_type comment supplied without value.')

        if entry_type == 'ipv4':
            if not all((address, names)):
                raise Exception('Address and Name(s) must be specified.')
            if not is_ipv4(address):
                raise exception.InvalidIPv4Address()

        if entry_type == 'ipv6':
            if not all((address, names)):
                raise Exception('Address and Name(s) must be specified.')
            if not is_ipv6(address):
                raise exception.InvalidIPv6Address()

        self.entry_type = entry_type
        self.address = address
        self.comment = comment
        self.names = names

    @staticmethod
    def get_entry_type(hosts_entry):
        """
        Return the type of entry for the line of hosts file passed
        :param hosts_entry: A line from the hosts file
        :return: comment | blank | ipv4 | ipv6
        """
        if hosts_entry[0] == "#":
            return 'comment'
        if hosts_entry[0] == "\n":
            return 'blank'
        entry_chunks = hosts_entry.split()
        if is_ipv4(entry_chunks[0]):
            return "ipv4"
        if is_ipv6(entry_chunks[0]):
            return "ipv6"
        else:
            return False

    @staticmethod
    def str_to_hostentry(entry):
        if isinstance(entry, str):
            line_parts = entry.strip().split()
            if line_parts[0][0] == '#':
                return HostsEntry(entry_type='comment', comment=line_parts[0])
            elif is_ipv4(line_parts[0]):
                if valid_hostnames(line_parts[1:]):
                    return HostsEntry(entry_type='ipv4', address=line_parts[0], names=line_parts[1:])
                else:
                    return False
            elif is_ipv6(line_parts[0]):
                if valid_hostnames(line_parts[1:]):
                    return HostsEntry(entry_type='ipv6', address=line_parts[0], names=line_parts[1:])
                else:
                    print("ipv6 address detected but invalid hostnames detected")
                    return False
            else:
                print("que?")
                return False

class Hosts(object):
    """ A hosts file. """
    def __init__(self, path=None):
        """
        Returns a list of all entries in the hosts file.
        Each entry is represented in the form of a dict.
        """
        self.entries = []
        if path:
            self.hosts_path = path
        else:
            self.hosts_path = self.determine_hosts_path()
        self.populate_entries()

    @staticmethod
    def determine_hosts_path(platform=None):
        """
        Return the hosts file path based on the supplied
        or detected platform.
        :param platform: override platform detection
        :return: path of hosts file
        """
        if not platform:
            platform = sys.platform
        if platform.startswith('win'):
            return r'c:\windows\system32\drivers\etc\hosts'
        else: 
            return '/etc/hosts'

    def write(self):
        """
        Write the list of host entries back to the hosts file.
        """
        with open(self.hosts_path, 'w') as hosts_file:
            for line in self.entries:
                if line.entry_type == 'comment':
                    hosts_file.write(line.comment)
                if line.entry_type == 'blank':
                    hosts_file.write("\n")
                if line.entry_type == 'ipv4':
                    hosts_file.write(
                        "{0}\t{1}\n".format(
                            line.address,
                            ' '.join(line.names),
                        )
                    )
                if line.entry_type == 'ipv6':
                    hosts_file.write(
                        "{0}\t{1}\n".format(
                            line.address,
                            ' '.join(line.names),))

    def add(self, entry=None, force=False):
        """
        Adds an entry to a host file.
        :param entry: An instance of HostsEntry
        :param force: Remove conflicting, existing instances first
        :return: True if successfully added to hosts file
        """

        if isinstance(entry, str):
            entry = HostsEntry.str_to_hostentry(entry)
        if entry.entry_type == "comment":
            existing = self.count(entry).get('comment_matches')
            if existing and int(existing) >= 1:
                return False
        if entry.entry_type == "ipv4" or entry.entry_type == "ipv6":
            existing = self.count(entry)
            existing_addresses = existing.get('address_matches')
            existing_names = existing.get('name_matches')
            if not force and (existing_addresses or existing_names):
                return False
            elif force:
                self.remove(entry)
        self.entries.append(entry)
        self.write()
        return True

    def count(self, entry=None):
        """
        Count the number of address, name or comment matches
        in the given HostsEntry instance or supplied values
        :param entry: An instance of HostsEntry
        :return: A dict listing the number of address, name and comment matches
        """
        if isinstance(entry, str):
            entry = HostsEntry.str_to_hostentry(entry)

        num_address_matches = 0
        num_name_matches = 0
        num_comment_matches = 0

        for host in self.entries:
            existing_names = host.names
            existing_host_address = host.address
            existing_comment = host.comment
            if entry.entry_type == "ipv4" or entry.entry_type == "ipv6":
                if all((existing_names, entry.names)) and \
                        set(entry.names).intersection(existing_names):
                    num_name_matches += 1
                if existing_host_address and \
                        existing_host_address == entry.address:
                    num_address_matches += 1
            if entry.entry_type == "comment":
                if existing_comment == entry.comment:
                    num_comment_matches += 1
        return {'address_matches': num_address_matches,
                'name_matches': num_name_matches,
                'comment_matches': num_comment_matches}

    def remove(self, entry=None):
        """
        Remove an entry from a hosts file
        :param entry: An instance of HostsEntry
        :return:
        """
        removed = 0
        removal_list = []
        for existing_entry in self.entries:
            if entry:
                if existing_entry.names and entry.names:
                    names_inter = set(
                        existing_entry.names).intersection(entry.names)
                    if any((existing_entry.address == entry.address,
                            existing_entry.names == entry.names,
                            names_inter)):
                        removal_list.append(existing_entry)
                        removed += 1
                if entry.comment and existing_entry.comment == entry.comment:
                    removal_list.append(existing_entry)
        for entry_to_remove in removal_list:
            self.entries.remove(entry_to_remove)
        self.write()
        if removed > 0:
            return True
        return False

    def populate_entries(self):
        """
        Read all hosts file entries from the hosts file specified
        and store them as HostEntry's in an instance of Hosts.
        """
        try:
            with open(self.hosts_path, 'r') as hosts_file:
                hosts_entries = [line for line in hosts_file]
                for hosts_entry in hosts_entries:
                    entry_type = HostsEntry.get_entry_type(hosts_entry)
                    if entry_type == "comment":
                        self.entries.append(HostsEntry(entry_type="comment",
                                                       comment=hosts_entry))
                    if entry_type == "blank":
                        self.entries.append(HostsEntry(entry_type="blank"))
                    if entry_type == "ipv4" or entry_type == "ipv6":
                        chunked_entry = hosts_entry.split()
                        self.entries.append(HostsEntry(entry_type=entry_type,
                                                       address=chunked_entry[0],
                                                       names=chunked_entry[1:]))
        except IOError:
            raise
